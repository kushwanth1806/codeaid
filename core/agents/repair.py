"""
repair.py
---------
Automatic repair agent.

Currently handles SAFE, deterministic fixes:
  - unused_import  → remove the offending import line(s)

All other issue types are flagged as "not auto-fixable" and left for the
LLM agent or human review.

Returns a list of repair result dicts:
  {
    "file":       str,
    "issue_type": str,
    "line":       int,
    "status":     "fixed" | "skipped" | "failed",
    "detail":     str,
    "patched":    str | None,   # new source after fix (for fixed issues)
  }
"""

import ast
import re
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repair_repository(files: List[Dict], issues: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Apply repairs to a repository's files.
    
    Parameters:
      files: list of {"path": str, "source": str}
      issues: list of issue dicts from scanner
    
    Returns:
      list of repair result dicts
    """
    return repair_issues(issues, files)


def summarize_repairs(repair_results: List[Dict]) -> Dict:
    """
    Summarize repair results.
    
    Returns:
      {"files_changed": int, "total_repairs": int, "details": []}
    """
    files_changed = len(set(r.get("file") for r in repair_results if r.get("status") == "fixed"))
    total_repairs = len([r for r in repair_results if r.get("status") == "fixed"])
    
    return {
        "files_changed": files_changed,
        "total_repairs": total_repairs,
        "details": repair_results,
    }


def repair_issues(issues: List[Dict], files: List[Dict]) -> List[Dict]:
    """
    Attempt to repair every fixable issue.

    Parameters
    ----------
    issues : list of issue dicts from scanner
    files  : list of {"path": str, "source": str}

    Returns
    -------
    list of repair result dicts; also mutates files[*]["source"] in place
    when a fix is applied so subsequent passes see updated code.
    """
    # Build quick lookup: path → file dict
    file_map: Dict[str, Dict] = {f["path"]: f for f in files}

    results: List[Dict] = []
    for issue in issues:
        if not issue.get("fixable"):
            results.append(_skipped(issue, "Issue marked as not auto-fixable."))
            continue

        itype = issue["issue_type"]
        path = issue["file"]
        file_entry = file_map.get(path)
        if file_entry is None:
            results.append(_failed(issue, "File not found in loaded files."))
            continue

        if itype == "unused_import":
            result = _fix_unused_import(issue, file_entry)
        else:
            result = _skipped(issue, f"No auto-repair for issue type '{itype}'.")

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Fix implementations
# ---------------------------------------------------------------------------

def _fix_unused_import(issue: Dict, file_entry: Dict) -> Dict:
    """
    Remove the unused import from the source.

    Strategy:
      1. Parse the AST to find the exact import node at the flagged line.
      2. If the import node imports *multiple* names, remove only the unused alias.
      3. If it imports a single name, remove the entire line.
    """
    source = file_entry["source"]
    target_name = _extract_import_name(issue["description"])
    target_line = issue["line"]  # 1-based

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _failed(issue, "Cannot parse source to apply fix.")

    lines = source.splitlines(keepends=True)

    for node in ast.walk(tree):
        if node.lineno != target_line:
            continue

        if isinstance(node, ast.Import):
            new_aliases = [
                a for a in node.names
                if not ((a.asname or a.name.split(".")[0]) == target_name)
            ]
            if not new_aliases:
                # Remove the entire line
                lines = _remove_lines(lines, node.lineno, node.end_lineno)
            else:
                # Rebuild the import with remaining names
                new_import = "import " + ", ".join(
                    (f"{a.name} as {a.asname}" if a.asname else a.name)
                    for a in new_aliases
                )
                lines[node.lineno - 1] = new_import + "\n"
            break

        elif isinstance(node, ast.ImportFrom):
            new_aliases = [
                a for a in node.names
                if not ((a.asname or a.name) == target_name)
            ]
            module = node.module or ""
            level_dots = "." * node.level
            if not new_aliases:
                lines = _remove_lines(lines, node.lineno, node.end_lineno)
            else:
                names_str = ", ".join(
                    (f"{a.name} as {a.asname}" if a.asname else a.name)
                    for a in new_aliases
                )
                lines[node.lineno - 1] = f"from {level_dots}{module} import {names_str}\n"
            break

    patched = "".join(lines)
    file_entry["source"] = patched  # mutate in place

    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": f"Removed unused import '{target_name}'.",
        "patched": patched,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remove_lines(lines: List[str], start: int, end: Optional[int]) -> List[str]:
    """Remove lines[start-1 : end] (1-based, inclusive)."""
    end = end or start
    return lines[: start - 1] + lines[end:]


def _extract_import_name(description: str) -> str:
    """Pull the name out of messages like: "Import 'os' is imported but never used." """
    m = re.search(r"Import '([^']+)'", description)
    return m.group(1) if m else ""


def _skipped(issue: Dict, detail: str) -> Dict:
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "skipped",
        "detail": detail,
        "patched": None,
    }


def _failed(issue: Dict, detail: str) -> Dict:
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "failed",
        "detail": detail,
        "patched": None,
    }
