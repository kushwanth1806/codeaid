"""
scanner.py
----------
Multi-language static analysis agent.

Detects language-agnostic and language-specific issues:
  - Syntax errors
  - Unused imports
  - Long functions  (> MAX_FUNC_LINES lines)
  - Too many parameters (> MAX_PARAMS) [Python only]
  - TODO / FIXME comments
  - Line too long
  - Trailing whitespace
  - Empty files

Supports: Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP

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
from pathlib import Path
from typing import List, Dict, Optional

from core.lang_detector import detect_languages, get_language_info
from core.agents.universal_analyzer import detect_universal_issues, detect_unused_imports

MAX_FUNC_LINES = 50
MAX_PARAMS = 7


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_repository(files: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Scan a list of files and return all detected issues.
    Supports multiple languages.
    
    Parameters
    ----------
    files : List[Dict]
        File list with "path" and "source" keys
    
    Returns
    -------
    List of issue dicts
    """
    # Detect languages in the repository
    detection = detect_languages(files)
    primary_lang = detection.get("primary_language", "python")
    
    return scan_files(files, primary_lang)


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


def scan_files(files: List[Dict], primary_language: str = "python") -> List[Dict]:
    """
    Run all checks on every file (multi-language support).

    Parameters
    ----------
    files : list of {"path": str, "source": str}
    primary_language : str, language to use for language-specific checks

    Returns
    -------
    list of issue dicts
    """
    all_issues: List[Dict] = []
    
    for f in files:
        path = f.get("path", "")
        source = f.get("source", "")
        
        # Detect file language
        file_ext = Path(path).suffix.lower()
        file_lang = _detect_file_language(path, primary_language)
        
        # Scan the file
        all_issues.extend(_scan_single(path, source, file_lang))
    
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

def _detect_file_language(path: str, primary_language: str = "python") -> str:
    """Detect the language of a file based on extension."""
    from core.lang_detector import LANGUAGE_EXTENSIONS
    
    ext = Path(path).suffix.lower()
    
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        if ext in exts:
            return lang
    
    return primary_language


def _scan_single(path: str, source: str, language: str = "python") -> List[Dict]:
    """
    Scan a single file for issues (multi-language support).
    
    Parameters
    ----------
    path : str
        File path
    source : str
        Source code
    language : str
        Detected language
    
    Returns
    -------
    List of issue dicts
    """
    issues: List[Dict] = []
    
    # Language-specific source syntax check
    if language == "python":
        # 1. Python syntax check first
        tree, syntax_issue = _check_python_syntax(path, source)
        if syntax_issue:
            issues.append(syntax_issue)
            return issues
        
        # 2. Python AST-based checks
        issues.extend(_check_unused_imports_python(path, source, tree))
        issues.extend(_check_long_functions_python(path, tree))
        issues.extend(_check_too_many_params_python(path, tree))
    else:
        # For non-Python, do basic syntax/structure check
        if not source.strip():
            issues.append({
                "file": path,
                "line": -1,
                "issue_type": "empty_file",
                "description": "File is empty",
                "severity": "warning",
                "fixable": False,
            })
        
        # Language-specific unused import detection
        issues.extend(detect_unused_imports(path, source, language))
    
    # 3. Universal checks (all languages)
    issues.extend(detect_universal_issues(path, source, language))
    
    return issues


def _check_python_syntax(path: str, source: str):
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


def _check_unused_imports_python(path: str, source: str, tree: ast.AST) -> List[Dict]:
    """Detect unused Python imports using AST."""
    issues: List[Dict] = []

    imported: Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname if alias.asname else alias.name
                imported[name] = node.lineno

    used: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
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


def _check_long_functions_python(path: str, tree: ast.AST) -> List[Dict]:
    """Flag long Python functions."""
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


def _check_too_many_params_python(path: str, tree: ast.AST) -> List[Dict]:
    """Flag Python functions with too many parameters."""
    issues: List[Dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
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
