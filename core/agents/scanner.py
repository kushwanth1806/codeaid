"""
scanner.py
----------
AST-based static analysis agent.

Detects:
  - Syntax errors
  - Unused imports
  - Long functions  (> MAX_FUNC_LINES lines)
  - Too many parameters (> MAX_PARAMS)
  - TODO / FIXME comments

Each issue is returned as a dict:
  {
    "file":        str,
    "line":        int  (1-based, -1 if N/A),
    "issue_type":  str,
    "description": str,
    "severity":    "error" | "warning" | "info",
    "fixable":     bool,
  }
"""

import ast
import re
import tokenize
import io
from typing import List, Dict

MAX_FUNC_LINES = 50
MAX_PARAMS = 7


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_repository(files: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Scan a list of files and return all detected issues.
    Alias for scan_files.
    """
    return scan_files(files)


def summarize_scan(issues: List[Dict]) -> Dict:
    """
    Summarize scan results into a summary dict.
    
    Returns:
      {"total_issues": int, "by_severity": {...}, "by_type": {...}}
    """
    summary = {
        "total_issues": len(issues),
        "by_severity": {},
        "by_type": {},
    }
    
    for issue in issues:
        severity = issue.get("severity", "info")
        issue_type = issue.get("issue_type", "unknown")
        
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1
    
    return summary


def scan_files(files: List[Dict]) -> List[Dict]:
    """
    Run all checks on every file.

    Parameters
    ----------
    files : list of {"path": str, "source": str}

    Returns
    -------
    list of issue dicts
    """
    all_issues: List[Dict] = []
    for f in files:
        all_issues.extend(_scan_single(f["path"], f["source"]))
    return all_issues


def scan_file(file_info: Dict) -> Dict:
    """
    Scan a single file and return results in a structured format.
    
    Parameters
    ----------
    file_info : dict with "content" and "relative_path" keys
    
    Returns
    -------
    dict with "issues" key containing list of detected issues
    """
    content = file_info.get("content", "")
    path = file_info.get("relative_path", "unknown.py")
    
    issues = _scan_single(path, content)
    
    # Convert to expected format with "type" field
    for issue in issues:
        if "issue_type" in issue and "type" not in issue:
            issue["type"] = issue["issue_type"]
    
    return {"issues": issues}


# ---------------------------------------------------------------------------
# Per-file scanning
# ---------------------------------------------------------------------------

def _scan_single(path: str, source: str) -> List[Dict]:
    issues: List[Dict] = []

    # 1. Syntax check first – if it fails we can't run AST checks
    tree, syntax_issue = _check_syntax(path, source)
    if syntax_issue:
        issues.append(syntax_issue)
        return issues  # no point running further checks

    # 2. AST-based checks
    issues.extend(_check_unused_imports(path, source, tree))
    issues.extend(_check_long_functions(path, tree))
    issues.extend(_check_too_many_params(path, tree))

    # 3. Token / regex-based checks
    issues.extend(_check_todo_comments(path, source))

    return issues


# ---------------------------------------------------------------------------
# Individual checkers
# ---------------------------------------------------------------------------

def _check_syntax(path: str, source: str):
    """Return (ast_tree, None) on success, (None, issue_dict) on failure."""
    try:
        tree = ast.parse(source, filename=path)
        return tree, None
    except SyntaxError as exc:
        issue = {
            "file": path,
            "line": exc.lineno or -1,
            "issue_type": "syntax_error",
            "description": f"SyntaxError: {exc.msg}",
            "severity": "error",
            "fixable": False,
        }
        return None, issue


def _check_unused_imports(path: str, source: str, tree: ast.AST) -> List[Dict]:
    """Detect imported names that are never referenced in the module body."""
    issues: List[Dict] = []

    # Collect imported names → line numbers
    imported: Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue  # wildcard – skip
                name = alias.asname if alias.asname else alias.name
                imported[name] = node.lineno

    # Collect all Name usages outside import statements
    used: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # capture root of attribute chain: foo.bar → foo
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used.add(root.id)

    for name, lineno in imported.items():
        if name not in used:
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "unused_import",
                "description": f"Import '{name}' is imported but never used.",
                "severity": "warning",
                "fixable": True,
            })

    return issues


def _check_long_functions(path: str, tree: ast.AST) -> List[Dict]:
    """Flag functions whose body exceeds MAX_FUNC_LINES lines."""
    issues: List[Dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or start
            length = end - start + 1
            if length > MAX_FUNC_LINES:
                issues.append({
                    "file": path,
                    "line": start,
                    "issue_type": "long_function",
                    "description": (
                        f"Function '{node.name}' is {length} lines long "
                        f"(limit: {MAX_FUNC_LINES}). Consider refactoring."
                    ),
                    "severity": "warning",
                    "fixable": False,
                })
    return issues


def _check_too_many_params(path: str, tree: ast.AST) -> List[Dict]:
    """Flag functions with more than MAX_PARAMS parameters."""
    issues: List[Dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            # count all kinds of arguments
            param_count = (
                len(args.args)
                + len(args.posonlyargs)
                + len(args.kwonlyargs)
                + (1 if args.vararg else 0)
                + (1 if args.kwarg else 0)
            )
            if param_count > MAX_PARAMS:
                issues.append({
                    "file": path,
                    "line": node.lineno,
                    "issue_type": "too_many_params",
                    "description": (
                        f"Function '{node.name}' has {param_count} parameters "
                        f"(limit: {MAX_PARAMS}). Use a config object or dataclass."
                    ),
                    "severity": "warning",
                    "fixable": False,
                })
    return issues


def _check_todo_comments(path: str, source: str) -> List[Dict]:
    """Detect TODO / FIXME / HACK / XXX annotations in comments."""
    issues: List[Dict] = []
    pattern = re.compile(r"#.*\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
    for lineno, line in enumerate(source.splitlines(), start=1):
        m = pattern.search(line)
        if m:
            tag = m.group(1).upper()
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "todo_comment",
                "description": f"{tag} comment found: {line.strip()[:120]}",
                "severity": "info",
                "fixable": False,
            })
    return issues
