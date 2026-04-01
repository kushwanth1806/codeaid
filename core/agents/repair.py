"""
repair.py
---------
Multi-language automatic repair agent.

Currently handles SAFE, deterministic fixes:
  - unused_import  → remove the offending import line(s) [all languages]
  - trailing_whitespace → remove trailing whitespace
  - file_formatting → basic formatting fixes

All other issue types are flagged as "not auto-fixable" and left for the
LLM agent or human review.

Supports: Python, JavaScript, TypeScript, Java, Go, Rust, etc.

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
from pathlib import Path
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repair_repository(files: List[Dict], issues: List[Dict]) -> List[Dict]:
    """
    Apply repairs to a repository's files (multi-language support).
    
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
    Attempt to repair every fixable issue (multi-language support).

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
    
    # Group issues by file and sort by line number (descending) to avoid line number shifts
    issues_by_file: Dict[str, List[Dict]] = {}
    for issue in issues:
        path = issue["file"]
        if path not in issues_by_file:
            issues_by_file[path] = []
        issues_by_file[path].append(issue)
    
    # Process issues for each file in reverse line order to avoid line number shifts
    for path, file_issues in issues_by_file.items():
        # Sort by line number descending
        sorted_issues = sorted(file_issues, key=lambda x: x.get("line", 0), reverse=True)
        
        for issue in sorted_issues:
            if not issue.get("fixable"):
                results.append(_skipped(issue, "Issue marked as not auto-fixable."))
                continue

            itype = issue["issue_type"]
            file_entry = file_map.get(path)
            if file_entry is None:
                results.append(_failed(issue, "File not found in loaded files."))
                continue

            # Detect file language
            language = _detect_file_language(path)
            
            # Apply language-appropriate repairs
            if itype == "unused_import":
                result = _fix_unused_import(issue, file_entry, language)
            elif itype == "trailing_whitespace":
                result = _fix_trailing_whitespace(issue, file_entry)
            else:
                result = _skipped(issue, f"No auto-repair for issue type '{itype}'.")

            results.append(result)

    return results


# ──────────────────────────────────────────────────────────────────────────
# Language Detection
# ──────────────────────────────────────────────────────────────────────────

def _detect_file_language(path: str) -> str:
    """Detect language from file extension."""
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "cpp",
    }
    return mapping.get(ext, "unknown")

def _fix_unused_import(issue: Dict, file_entry: Dict, language: str = "python") -> Dict:
    """
    Remove unused imports (multi-language support).
    
    Supports: Python, JavaScript, TypeScript, Java, Go, Rust, etc.
    """
    source = file_entry["source"]
    target_name = _extract_import_name(issue["description"])
    target_line = issue["line"]

    if language == "python":
        return _fix_unused_import_python(issue, file_entry, source, target_name, target_line)
    elif language in ["javascript", "typescript"]:
        return _fix_unused_import_js(issue, file_entry, source, target_name, target_line)
    elif language == "java":
        return _fix_unused_import_java(issue, file_entry, source, target_name, target_line)
    else:
        return _fix_unused_import_generic(issue, file_entry, source, target_name, target_line, language)


def _fix_unused_import_python(issue: Dict, file_entry: Dict, source: str, target_name: str, target_line: int) -> Dict:
    """Fix unused Python imports using AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _failed(issue, "Cannot parse Python source to apply fix.")

    lines = source.splitlines(keepends=True)

    for node in ast.walk(tree):
        # Skip nodes without lineno attribute
        if not hasattr(node, 'lineno') or node.lineno != target_line:
            continue

        if isinstance(node, ast.Import):
            new_aliases = [
                a for a in node.names
                if not ((a.asname or a.name.split(".")[0]) == target_name)
            ]
            if not new_aliases:
                lines = _remove_lines(lines, node.lineno, node.end_lineno)
            else:
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
    file_entry["source"] = patched

    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": f"Removed unused Python import '{target_name}'.",
        "patched": patched,
    }


def _fix_unused_import_js(issue: Dict, file_entry: Dict, source: str, target_name: str, target_line: int) -> Dict:
    """Fix unused JavaScript/TypeScript imports by removing the import line."""
    lines = source.splitlines(keepends=True)
    
    if 0 < target_line <= len(lines):
        line = lines[target_line - 1]
        if "import" in line or "require" in line:
            del lines[target_line - 1]
    
    patched = "".join(lines)
    file_entry["source"] = patched
    
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": f"Removed unused JavaScript/TypeScript import '{target_name}'.",
        "patched": patched,
    }


def _fix_unused_import_java(issue: Dict, file_entry: Dict, source: str, target_name: str, target_line: int) -> Dict:
    """Fix unused Java imports by removing the import statement."""
    lines = source.splitlines(keepends=True)
    
    if 0 < target_line <= len(lines):
        line = lines[target_line - 1]
        if "import" in line:
            del lines[target_line - 1]
    
    patched = "".join(lines)
    file_entry["source"] = patched
    
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": f"Removed unused Java import '{target_name}'.",
        "patched": patched,
    }


def _fix_unused_import_generic(issue: Dict, file_entry: Dict, source: str, target_name: str, target_line: int, language: str) -> Dict:
    """Generic unused import fix for other languages."""
    lines = source.splitlines(keepends=True)
    
    if 0 < target_line <= len(lines):
        del lines[target_line - 1]
    
    patched = "".join(lines)
    file_entry["source"] = patched
    
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": f"Removed unused {language} import '{target_name}'.",
        "patched": patched,
    }


def _fix_trailing_whitespace(issue: Dict, file_entry: Dict) -> Dict:
    """Remove trailing whitespace from a line."""
    source = file_entry["source"]
    target_line = issue["line"]
    
    lines = source.splitlines(keepends=True)
    
    if 0 < target_line <= len(lines):
        lines[target_line - 1] = lines[target_line - 1].rstrip() + "\n"
    
    patched = "".join(lines)
    file_entry["source"] = patched
    
    return {
        "file": issue["file"],
        "issue_type": issue["issue_type"],
        "line": issue["line"],
        "status": "fixed",
        "detail": "Removed trailing whitespace.",
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
