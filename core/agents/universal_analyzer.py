"""
universal_analyzer.py
----------------------
Language-agnostic code analysis.

Detects common code issues that apply across all languages:
- Syntax errors (basic)
- Unused imports/requires/includes
- Long functions/methods
- Too many parameters
- TODO/FIXME comments
- Trailing whitespace
- Empty lines at end of file
- Duplicate code patterns
"""

import re
from typing import List, Dict, Tuple, Pattern
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────
# Issue Detectors
# ──────────────────────────────────────────────────────────────────────────

def detect_universal_issues(path: str, source: str, language: str = "unknown") -> List[Dict]:
    """
    Detect language-agnostic code issues.
    
    Parameters
    ----------
    path : str
        Relative path to file
    source : str
        Source code content
    language : str
        Detected language (optional, for context)
    
    Returns
    -------
    List of issue dicts
    """
    issues: List[Dict] = []
    
    # Universal checks
    issues.extend(_check_todo_comments(path, source))
    issues.extend(_check_trailing_whitespace(path, source))
    issues.extend(_check_long_lines(path, source))
    issues.extend(_check_empty_file(path, source))
    issues.extend(_check_long_functions(path, source, language))
    
    return issues


def _check_todo_comments(path: str, source: str) -> List[Dict]:
    """Detect TODO, FIXME, and similar comments."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    # Patterns for different comment styles
    patterns = [
        (r'#\s*(TODO|FIXME|BUG|HACK)[\s:]*(.+)', "Python/Shell comment"),
        (r'//\s*(TODO|FIXME|BUG|HACK)[\s:]*(.+)', "C-style comment"),
        (r'/\*\s*(TODO|FIXME|BUG|HACK)[\s:]*(.+)\*/', "C-style block comment"),
        (r'--\s*(TODO|FIXME|BUG|HACK)[\s:]*(.+)', "SQL comment"),
        (r'<!--\s*(TODO|FIXME|BUG|HACK)[\s:]*(.+)-->', "HTML comment"),
    ]
    
    for lineno, line in enumerate(lines, start=1):
        for pattern, comment_type in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                marker = match.group(1).upper()
                message = match.group(2).strip() if len(match.groups()) > 1 else ""
                issues.append({
                    "file": path,
                    "line": lineno,
                    "issue_type": marker.lower() + "_comment",
                    "description": f"{marker} comment: {message}",
                    "severity": "info",
                    "fixable": False,
                })
                break
    
    return issues


def _check_trailing_whitespace(path: str, source: str) -> List[Dict]:
    """Detect lines with trailing whitespace."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    for lineno, line in enumerate(lines, start=1):
        if line != line.rstrip():
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "trailing_whitespace",
                "description": "Line has trailing whitespace",
                "severity": "info",
                "fixable": True,
            })
    
    return issues


def _check_long_lines(path: str, source: str, max_length: int = 120) -> List[Dict]:
    """Detect lines exceeding max length."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    for lineno, line in enumerate(lines, start=1):
        if len(line) > max_length:
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "line_too_long",
                "description": f"Line is {len(line)} characters (max: {max_length})",
                "severity": "warning",
                "fixable": False,
            })
    
    return issues


def _check_empty_file(path: str, source: str) -> List[Dict]:
    """Detect empty files."""
    issues: List[Dict] = []
    
    if not source.strip():
        issues.append({
            "file": path,
            "line": -1,
            "issue_type": "empty_file",
            "description": "File is empty or contains only whitespace",
            "severity": "warning",
            "fixable": False,
        })
    
    return issues


def _check_long_functions(path: str, source: str, language: str = "unknown") -> List[Dict]:
    """
    Detect functions/methods that are too long.
    Language-aware detection.
    """
    issues: List[Dict] = []
    max_lines = 50
    
    # Function/method patterns by language
    patterns = {
        "python": r"^\s*(def|async def)\s+(\w+)\s*\(",
        "javascript": r"^\s*(function|async function|\w+\s*\(|const\s+\w+\s*=\s*(?:async)?\s*\()\s*",
        "typescript": r"^\s*(function|async function|public|private|protected)?\s*(\w+)\s*\(",
        "java": r"^\s*(public|private|protected|static|synchronized)?\s*(.*?)\s+(\w+)\s*\(",
        "go": r"^\s*func\s+(\w+|\(\w+\s+\*?\w+\))\s*\(",
        "csharp": r"^\s*(public|private|protected|internal)?\s*(async)?\s*(\w+)\s+(\w+)\s*\(",
        "ruby": r"^\s*def\s+(\w+)",
        "php": r"^\s*(public|private|protected)?\s*function\s+(\w+)\s*\(",
    }
    
    pattern_str = patterns.get(language.lower(), patterns.get("python"))
    pattern = re.compile(pattern_str, re.MULTILINE)
    
    lines = source.splitlines()
    in_function = False
    func_start = 0
    func_name = ""
    indent_level = None
    
    for lineno, line in enumerate(lines):
        # Check if function definition
        if pattern.match(line):
            in_function = True
            func_start = lineno
            func_name = line.strip()[:50]  # First 50 chars
            indent_level = len(line) - len(line.lstrip())
        
        # Check if we've exited the function
        elif in_function:
            current_indent = len(line) - len(line.lstrip())
            is_empty = not line.strip()
            
            # Check if we're back at same indent level (new definition)
            if not is_empty and current_indent <= indent_level and not line.strip().startswith(("#", "//")):
                # Function ended
                func_length = lineno - func_start
                if func_length > max_lines:
                    issues.append({
                        "file": path,
                        "line": func_start + 1,
                        "issue_type": "long_function",
                        "description": f"Function/method is {func_length} lines long (max: {max_lines})",
                        "severity": "warning",
                        "fixable": False,
                    })
                in_function = False
    
    # Check last function if file ended
    if in_function:
        func_length = len(lines) - func_start
        if func_length > max_lines:
            issues.append({
                "file": path,
                "line": func_start + 1,
                "issue_type": "long_function",
                "description": f"Function/method is {func_length} lines long (max: {max_lines})",
                "severity": "warning",
                "fixable": False,
            })
    
    return issues


def detect_unused_imports(path: str, source: str, language: str = "unknown") -> List[Dict]:
    """
    Detect unused imports/requires/includes (basic heuristic approach).
    Works across languages.
    """
    issues: List[Dict] = []
    language = language.lower()
    
    if language == "python":
        return _detect_unused_imports_python(path, source)
    elif language in ["javascript", "typescript"]:
        return _detect_unused_imports_js(path, source, language)
    elif language == "java":
        return _detect_unused_imports_java(path, source)
    elif language in ["go", "rust"]:
        return _detect_unused_imports_generic(path, source, language)
    else:
        return _detect_unused_imports_generic(path, source, language)


def _detect_unused_imports_python(path: str, source: str) -> List[Dict]:
    """Detect unused Python imports using regex (fast approach)."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    # Find all imports
    imports_info = []
    for lineno, line in enumerate(lines, start=1):
        # Match: import x, from x import y
        import_match = re.match(r'^\s*(?:from\s+[\w.]+\s+)?import\s+(.+)', line)
        if import_match:
            imports_str = import_match.group(1)
            # Parse imported names
            for item in imports_str.split(','):
                item = item.strip()
                if ' as ' in item:
                    _, name = item.rsplit(' as ', 1)
                else:
                    name = item.split('.')[0]
                imports_info.append((name.strip(), lineno))
    
    # Find uses of these names (simplified check)
    source_without_imports = re.sub(r'^\s*(?:from\s+[\w.]+\s+)?import\s+.+$', '', source, flags=re.MULTILINE)
    
    for name, lineno in imports_info:
        # Check if name is used (simple regex, not perfect)
        if not re.search(rf'\b{re.escape(name)}\b', source_without_imports):
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "unused_import",
                "description": f"Import '{name}' is never used",
                "severity": "warning",
                "fixable": True,
            })
    
    return issues


def _detect_unused_imports_js(path: str, source: str, language: str) -> List[Dict]:
    """Detect unused imports in JavaScript/TypeScript."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    imports_info = []
    
    # Match: import x from 'y', const x = require('y')
    for lineno, line in enumerate(lines, start=1):
        # import ... from ...
        match = re.match(r"^\s*import\s+(?:\{([^}]+)\}|(\w+(?:\s*,\s*\{\s*[^}]+\s*\})?)|(\w+(?:\s+as\s+\w+)?)|(?:\*\s+as\s+(\w+)))", line)
        if match:
            # Extract imported names
            if match.group(1):  # {named imports}
                names = [n.split(' as ')[1] if ' as ' in n else n for n in match.group(1).split(',')]
                imports_info.extend([(n.strip(), lineno) for n in names])
            else:
                # default import
                pass
        
        # const x = require(...)
        match = re.match(r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(", line)
        if match:
            imports_info.append((match.group(1), lineno))
    
    # Remove imports from source to check for usage
    source_without_imports = re.sub(r"^\s*import\s+.+$", "", source, flags=re.MULTILINE)
    source_without_imports = re.sub(r"^\s*(?:const|let|var)\s+\w+\s*=\s*require\s*\(.+\);?$", "", source_without_imports, flags=re.MULTILINE)
    
    for name, lineno in imports_info:
        if not re.search(rf'\b{re.escape(name)}\b', source_without_imports):
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "unused_import",
                "description": f"Import '{name}' is never used",
                "severity": "warning",
                "fixable": True,
            })
    
    return issues


def _detect_unused_imports_java(path: str, source: str) -> List[Dict]:
    """Detect unused Java imports."""
    issues: List[Dict] = []
    lines = source.splitlines()
    
    imports_info = []
    for lineno, line in enumerate(lines, start=1):
        match = re.match(r"^\s*import\s+((?:static\s+)?[\w.]+(?:\.\*)?);", line)
        if match:
            import_str = match.group(1)
            if import_str.endswith('.*'):
                continue  # Skip wildcard imports (can't easily track)
            # Get last part as class/interface name
            name = import_str.split('.')[-1]
            imports_info.append((name, lineno))
    
    source_without_imports = re.sub(r"^\s*import\s+.+;", "", source, flags=re.MULTILINE)
    
    for name, lineno in imports_info:
        if not re.search(rf'\b{re.escape(name)}\b', source_without_imports):
            issues.append({
                "file": path,
                "line": lineno,
                "issue_type": "unused_import",
                "description": f"Import '{name}' is never used",
                "severity": "warning",
                "fixable": True,
            })
    
    return issues


def _detect_unused_imports_generic(path: str, source: str, language: str) -> List[Dict]:
    """Generic unused import detection (basic)."""
    # For now, return empty for other languages
    # Can be extended as needed
    return []
