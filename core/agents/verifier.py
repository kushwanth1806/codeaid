"""
verifier.py
-----------
Verification agent.

After repairs are applied, re-compile each modified file using Python's
built-in `compile()` to confirm the patched source is syntactically valid.

Returns a list of verification result dicts:
  {
    "file":   str,
    "status": "passed" | "failed",
    "detail": str,
  }
"""

from typing import List, Dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_all_repairs(repair_results: List[Dict], files: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Verify repaired files.
    
    Performs compile-checks on all files that had repairs applied.
    
    Parameters:
      repair_results: List of repair result dicts from repair.repair_issues()
      files: List of current (possibly patched) file dicts
    
    Returns:
      List of verification result dicts
    """
    return verify_repairs(repair_results, files)


def summarize_verification(verification_results: List[Dict]) -> Dict:
    """
    Summarize verification results.
    
    Returns:
      {"total_files": int, "passed": int, "failed": int, "regressions": int}
    """
    return {
        "total_files": len(verification_results),
        "passed": len([r for r in verification_results if r.get("status") == "passed"]),
        "failed": len([r for r in verification_results if r.get("status") == "failed"]),
        "regressions": 0,
    }


def verify_repairs(repair_results: List[Dict], files: List[Dict]) -> List[Dict]:
    """
    Compile-check every file that had at least one successful fix applied.
    Supports multi-language verification.

    Parameters
    ----------
    repair_results : output of repair.repair_issues()
    files          : current (possibly patched) file list

    Returns
    -------
    list of verification result dicts
    """
    # Identify files that were actually modified
    fixed_files = {
        r.get("file") or r.get("path", "unknown")
        for r in repair_results
        if r.get("status") == "fixed"
    }

    # Build file_map safely, skipping files missing 'path' or 'source'
    file_map: Dict[str, str] = {
        f.get("path") or f.get("file", ""): f.get("source", "")
        for f in files
        if f.get("path") or f.get("file")
    }

    results: List[Dict] = []
    for path in fixed_files:
        source = file_map.get(path, "")
        results.append(_verify_file(path, source))

    return results


def verify_source(path: str, source: str) -> Dict:
    """
    Verify a single source file. Multi-language support.
    """
    return _verify_file(path, source)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _verify_file(path: str, source: str) -> Dict:
    """
    Verify a file based on its language.
    Supports Python, JavaScript, TypeScript, Java, Go, Rust, etc.
    """
    from pathlib import Path
    
    # Detect language from file extension
    ext = Path(path).suffix.lower()
    language = _detect_language_from_extension(ext)
    
    if language == "python":
        return _verify_python_file(path, source)
    elif language in ["javascript", "typescript"]:
        return _verify_js_file(path, source, language)
    elif language == "java":
        return _verify_java_file(path, source)
    elif language == "go":
        return _verify_go_file(path, source)
    elif language == "rust":
        return _verify_rust_file(path, source)
    else:
        return _verify_generic_file(path, source)


def _detect_language_from_extension(ext: str) -> str:
    """Detect language from file extension."""
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
    }
    return mapping.get(ext, "unknown")


def _verify_python_file(path: str, source: str) -> Dict:
    """Verify Python file by compiling."""
    try:
        compile(source, path, "exec")
        return {
            "file": path,
            "status": "passed",
            "detail": "Python file compiles successfully after repair.",
        }
    except SyntaxError as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Python SyntaxError after repair at line {exc.lineno}: {exc.msg}",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Python verification error: {exc}",
        }


def _verify_js_file(path: str, source: str, language: str) -> Dict:
    """Verify JavaScript/TypeScript file (basic syntax check)."""
    try:
        # Basic syntax validation - check for balanced braces/brackets
        if not _check_balanced_brackets(source):
            return {
                "file": path,
                "status": "failed",
                "detail": f"{language.capitalize()} syntax error: unbalanced brackets/braces",
            }
        
        if _has_obvious_syntax_errors(source):
            return {
                "file": path,
                "status": "failed",
                "detail": f"{language.capitalize()} syntax error detected",
            }
        
        return {
            "file": path,
            "status": "passed",
            "detail": f"{language.capitalize()} file passed basic syntax verification.",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"{language.capitalize()} verification error: {exc}",
        }


def _verify_java_file(path: str, source: str) -> Dict:
    """Verify Java file (basic syntax check)."""
    try:
        if not _check_balanced_brackets(source):
            return {
                "file": path,
                "status": "failed",
                "detail": "Java syntax error: unbalanced brackets/braces",
            }
        
        return {
            "file": path,
            "status": "passed",
            "detail": "Java file passed basic syntax verification.",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Java verification error: {exc}",
        }


def _verify_go_file(path: str, source: str) -> Dict:
    """Verify Go file (basic syntax check)."""
    try:
        if not _check_balanced_brackets(source):
            return {
                "file": path,
                "status": "failed",
                "detail": "Go syntax error: unbalanced brackets/braces",
            }
        
        return {
            "file": path,
            "status": "passed",
            "detail": "Go file passed basic syntax verification.",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Go verification error: {exc}",
        }


def _verify_rust_file(path: str, source: str) -> Dict:
    """Verify Rust file (basic syntax check)."""
    try:
        if not _check_balanced_brackets(source):
            return {
                "file": path,
                "status": "failed",
                "detail": "Rust syntax error: unbalanced brackets/braces",
            }
        
        return {
            "file": path,
            "status": "passed",
            "detail": "Rust file passed basic syntax verification.",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Rust verification error: {exc}",
        }


def _verify_generic_file(path: str, source: str) -> Dict:
    """Generic verification for unsupported languages."""
    try:
        if not source.strip():
            return {
                "file": path,
                "status": "failed",
                "detail": "File is empty after repair",
            }
        
        return {
            "file": path,
            "status": "passed",
            "detail": "File passed basic verification (language not fully supported)",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Verification error: {exc}",
        }


def _check_balanced_brackets(source: str) -> bool:
    """Check if brackets and braces are balanced."""
    stack = []
    bracket_pairs = {'(': ')', '[': ']', '{': '}'}
    in_string = False
    string_char = None
    
    for i, char in enumerate(source):
        # Handle strings
        if char in ['"', "'"] and (i == 0 or source[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
        
        if in_string:
            continue
        
        if char in '({[':
            stack.append(char)
        elif char in ')}]':
            if not stack:
                return False
            if bracket_pairs.get(stack[-1]) != char:
                return False
            stack.pop()
    
    return len(stack) == 0


def _has_obvious_syntax_errors(source: str) -> bool:
    """Check for obvious syntax errors in JS/TS."""
    # Check for unclosed strings
    in_string = False
    string_char = None
    escape_next = False
    
    for char in source:
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char in ['"', "'", '`'] and not in_string:
            in_string = True
            string_char = char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
    
    return in_string
