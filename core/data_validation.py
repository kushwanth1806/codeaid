"""
data_validation.py
------------------
Data validation and normalization layer for CodeAid.

Ensures all data structures have consistent fields and safe defaults.
Prevents KeyErrors, TypeErrors, and other data-related crashes.

Key Functions:
  - normalize_issue() → standardizes issue dicts from scanner
  - validate_issue() → checks issue dict for required fields
  - validate_file() → checks file dict for required fields
  - enrich_issue_for_ui() → adds UI-specific fields to issues
  - normalize_scan_results() → batch normalize all issues
"""

from typing import List, Dict, Optional, Tuple
import re


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

ISSUE_SEVERITY_LEVELS = {"critical", "error", "warning", "info", "note"}
ISSUE_TYPES = {
    "syntax_error",
    "unused_import",
    "long_function",
    "too_many_params",
    "todo_comment",
    "fixme_comment",
    "line_too_long",
    "trailing_whitespace",
    "empty_file",
    "undefined_variable",
    "missing_docstring",
    "complexity_warning",
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "error": "🔴",
    "warning": "🟡",
    "info": "🔵",
    "note": "⚪",
}

SEVERITY_ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3, "note": 4}


# ─────────────────────────────────────────────────────────────────────────────
# ISSUE NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────


def normalize_issue(issue: Optional[Dict]) -> Dict:
    """
    Ensure an issue dict has all required fields with safe defaults.

    Takes an issue from scanner and enriches it with:
      - safe defaults for missing fields
      - type normalizations
      - UI-ready fields

    Args:
        issue: Raw issue dict from scanner (may have missing fields)

    Returns:
        Normalized issue dict with all required fields
    """
    if issue is None:
        issue = {}

    if not isinstance(issue, dict):
        return _empty_issue("Invalid issue structure")

    # --- Core Fields (from scanner) ---
    file_path = issue.get("file") or issue.get("path") or "unknown"
    line_no = _extract_line_number(issue.get("line"))
    issue_type = _normalize_issue_type(
        issue.get("issue_type") or issue.get("type") or "unknown"
    )
    severity = _normalize_severity(
        issue.get("severity") or issue.get("level") or "warning"
    )
    description = (
        issue.get("description") or issue.get("message") or "Code issue detected"
    )
    is_fixable = issue.get("fixable", False)

    # --- Enriched Fields (for UI) ---
    icon = SEVERITY_ICONS.get(severity, "⚪")
    title = _get_issue_title(issue_type)
    message = _get_issue_message(description, issue_type)
    summary = _get_issue_summary(issue_type, description)
    impact = _get_issue_impact(issue_type, severity)
    tip = _get_issue_tip(issue_type)
    snippet = issue.get("snippet") or issue.get("code_snippet") or ""

    # --- Relative Path (computed if not present) ---
    relative_path = issue.get("relative_path") or _compute_relative_path(
        file_path
    )

    return {
        # Core fields
        "file": file_path,
        "path": file_path,
        "line": line_no,
        "issue_type": issue_type,
        "type": issue_type,  # For backward compatibility
        "severity": severity,
        "level": severity,  # Alias
        "description": description,
        "message": message,  # Alias
        "fixable": is_fixable,
        # UI fields
        "icon": icon,
        "title": title,
        "summary": summary,
        "impact": impact,
        "tip": tip,
        "snippet": snippet,
        "relative_path": relative_path,
        # Metadata
        "has_explanation": True,
        "auto_fixable": is_fixable,
    }


def validate_issue(issue: Dict) -> Tuple[bool, List[str]]:
    """
    Validate an issue dict for completeness and correctness.

    Args:
        issue: Issue dict to validate

    Returns:
        (is_valid: bool, errors: List[str])
    """
    errors = []

    if not isinstance(issue, dict):
        return False, ["Issue must be a dictionary"]

    # Check required fields
    if not issue.get("file") and not issue.get("path"):
        errors.append("Missing 'file' or 'path' field")

    if not issue.get("issue_type") and not issue.get("type"):
        errors.append("Missing 'issue_type' or 'type' field")

    if "line" in issue and issue["line"] is not None:
        try:
            line = int(issue["line"])
            if line < -1:
                errors.append(f"Line number must be >= -1, got {line}")
        except (ValueError, TypeError):
            errors.append(f"Line number must be integer, got {type(issue['line'])}")

    severity = issue.get("severity") or issue.get("level")
    if severity and severity not in ISSUE_SEVERITY_LEVELS:
        errors.append(f"Invalid severity '{severity}', expected one of {ISSUE_SEVERITY_LEVELS}")

    issue_type = issue.get("issue_type") or issue.get("type")
    if issue_type and not _is_valid_issue_type(issue_type):
        errors.append(f"Unknown issue_type '{issue_type}'")

    if "fixable" in issue and not isinstance(issue["fixable"], bool):
        errors.append(f"'fixable' must be bool, got {type(issue['fixable'])}")

    return len(errors) == 0, errors


def validate_file(file_dict: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a file dict for completeness.

    Args:
        file_dict: File dict to validate

    Returns:
        (is_valid: bool, errors: List[str])
    """
    errors = []

    if not isinstance(file_dict, dict):
        return False, ["File must be a dictionary"]

    if "path" not in file_dict and "file" not in file_dict:
        errors.append("Missing 'path' or 'file' field")

    if "source" not in file_dict and "content" not in file_dict:
        errors.append("Missing 'source' or 'content' field")

    return len(errors) == 0, errors


# ─────────────────────────────────────────────────────────────────────────────
# BATCH NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────


def normalize_scan_results(scan_results: Optional[List[Dict]]) -> List[Dict]:
    """
    Normalize all issues from scan_repository() output.

    Args:
        scan_results: List of issue dicts from scanner

    Returns:
        List of normalized issue dicts (never returns None)
    """
    if scan_results is None:
        return []

    if not isinstance(scan_results, list):
        return [_empty_issue(f"Invalid scan results type: {type(scan_results)}")]

    normalized = []
    for issue in scan_results:
        try:
            normalized.append(normalize_issue(issue))
        except Exception as exc:
            # Gracefully handle any normalization errors
            normalized.append(
                _empty_issue(f"Failed to normalize issue: {exc}")
            )

    return normalized


def normalize_repair_results(repair_results: Optional[List[Dict]]) -> List[Dict]:
    """
    Normalize all repair result dicts.

    Args:
        repair_results: List of repair result dicts

    Returns:
        List of normalized repair result dicts (never returns None)
    """
    if repair_results is None:
        return []

    if not isinstance(repair_results, list):
        return []

    normalized = []
    for result in repair_results:
        if isinstance(result, dict):
            normalized.append({
                "file": result.get("file") or "unknown",
                "relative_path": result.get("relative_path") or result.get("file") or "unknown",
                "issue_type": result.get("issue_type") or "unknown",
                "line": result.get("line") or -1,
                "status": result.get("status") or "unknown",
                "detail": result.get("detail") or "",
                "patched": result.get("patched"),
            })

    return normalized


def enrich_issues_for_ui(issues: List[Dict]) -> List[Dict]:
    """
    Enrich all issues with UI-specific fields.

    Args:
        issues: List of normalized issues

    Returns:
        List of issues ready for UI rendering
    """
    enriched = []
    for issue in issues:
        if isinstance(issue, dict):
            enriched.append(normalize_issue(issue))
        else:
            enriched.append(_empty_issue("Invalid issue format"))

    return enriched


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _empty_issue(reason: str = "Unknown issue") -> Dict:
    """Create a safe empty issue with default values."""
    return {
        "file": "unknown",
        "path": "unknown",
        "line": -1,
        "issue_type": "unknown",
        "type": "unknown",
        "severity": "info",
        "level": "info",
        "description": reason,
        "message": reason,
        "fixable": False,
        "icon": "⚪",
        "title": "Unknown Issue",
        "summary": reason,
        "impact": "Unable to determine impact",
        "tip": "Review the error message above for details",
        "snippet": "",
        "relative_path": "unknown",
        "has_explanation": False,
        "auto_fixable": False,
    }


def _extract_line_number(line_value: Optional[int]) -> int:
    """Safely extract line number, defaulting to -1 if invalid."""
    try:
        if line_value is None:
            return -1
        line_int = int(line_value)
        return max(-1, line_int)  # Never return negative except -1
    except (ValueError, TypeError):
        return -1


def _normalize_severity(severity_str: Optional[str]) -> str:
    """Normalize severity to valid level."""
    if not severity_str:
        return "warning"

    severity_lower = str(severity_str).lower().strip()

    # Map common aliases
    aliases = {
        "error": "error",
        "err": "error",
        "critical": "critical",
        "crit": "critical",
        "fatal": "critical",
        "warning": "warning",
        "warn": "warning",
        "info": "info",
        "information": "info",
        "note": "note",
        "debug": "info",
    }

    return aliases.get(severity_lower, "warning")


def _normalize_issue_type(issue_type_str: Optional[str]) -> str:
    """Normalize issue type to known types."""
    if not issue_type_str:
        return "unknown"

    type_lower = str(issue_type_str).lower().strip().replace("-", "_").replace(" ", "_")

    # Map common aliases
    aliases = {
        "syntax": "syntax_error",
        "syntax_error": "syntax_error",
        "syntaxerror": "syntax_error",
        "import": "unused_import",
        "unused_import": "unused_import",
        "long_func": "long_function",
        "long_function": "long_function",
        "too_many_params": "too_many_params",
        "too_many_params": "too_many_params",
        "too_many_arguments": "too_many_params",
        "todo": "todo_comment",
        "todo_comment": "todo_comment",
        "fixme": "fixme_comment",
        "fixme_comment": "fixme_comment",
        "line_too_long": "line_too_long",
        "line_length": "line_too_long",
        "trailing": "trailing_whitespace",
        "trailing_whitespace": "trailing_whitespace",
        "empty": "empty_file",
        "empty_file": "empty_file",
    }

    return aliases.get(type_lower, type_lower)


def _is_valid_issue_type(issue_type: str) -> bool:
    """Check if issue type is known or reasonable."""
    normalized = _normalize_issue_type(issue_type)
    # Accept either known types or reasonable custom types
    return normalized in ISSUE_TYPES or "_" in normalized or normalized.isalnum()


def _compute_relative_path(file_path: str) -> str:
    """Extract relative path from full path."""
    if not file_path:
        return "unknown"

    # Remove common temp dir prefixes
    path_str = str(file_path)
    for prefix in ["/tmp/", "\\tmp\\", "/var/tmp/", "C:\\Temp\\", "/Users//Desktop/"]:
        if prefix in path_str:
            path_str = path_str.split(prefix)[1]
            break

    return path_str


def _get_issue_title(issue_type: str) -> str:
    """Get human-readable title for issue type."""
    titles = {
        "syntax_error": "Syntax Error",
        "unused_import": "Unused Import",
        "long_function": "Long Function",
        "too_many_params": "Too Many Parameters",
        "todo_comment": "TODO Comment",
        "fixme_comment": "FIXME Comment",
        "line_too_long": "Line Too Long",
        "trailing_whitespace": "Trailing Whitespace",
        "empty_file": "Empty File",
        "undefined_variable": "Undefined Variable",
        "missing_docstring": "Missing Docstring",
        "complexity_warning": "High Complexity",
    }
    return titles.get(issue_type, "Code Issue")


def _get_issue_message(description: str, issue_type: str) -> str:
    """Generate user-friendly message for issue."""
    if description and description != "Code issue detected":
        return description

    messages = {
        "syntax_error": "Python code contains syntax errors and cannot be parsed",
        "unused_import": "Import statement is declared but never used",
        "long_function": "Function exceeds recommended line count",
        "too_many_params": "Function has too many parameters",
        "todo_comment": "TODO annotation indicates incomplete code",
        "fixme_comment": "FIXME annotation indicates broken code",
        "line_too_long": "Line exceeds recommended length",
        "trailing_whitespace": "Line has unnecessary trailing whitespace",
        "empty_file": "File is empty or contains only whitespace",
    }

    return messages.get(issue_type, "Code quality issue detected")


def _get_issue_summary(issue_type: str, description: str) -> str:
    """Get one-line summary for issue."""
    if description:
        # Truncate to ~100 chars
        return description[:100] + ("..." if len(description) > 100 else "")

    summaries = {
        "syntax_error": "Invalid Python syntax prevents parsing",
        "unused_import": "Remove unnecessary import",
        "long_function": "Consider breaking into smaller functions",

        "too_many_params": "Reduce function parameters",
        "todo_comment": "Incomplete work marked for later",
        "fixme_comment": "Known bug or issue in code",
        "line_too_long": "Shorten line for readability",
        "trailing_whitespace": "Remove whitespace at end of line",
        "empty_file": "File contains no actual code",
    }

    return summaries.get(issue_type, "Code quality issue")


def _get_issue_impact(issue_type: str, severity: str) -> str:
    """Describe the impact of this issue."""
    if severity == "critical":
        return "🔴 Critical: Prevents code execution or deployment"
    elif severity == "error":
        return "🔴 High: Likely causes runtime failures"
    elif severity == "warning":
        return "🟡 Medium: May cause issues; code quality concern"
    else:
        return "🔵 Low: Minor code quality or maintainability issue"


def _get_issue_tip(issue_type: str) -> str:
    """Get actionable tip for fixing issue."""
    tips = {
        "syntax_error": "Check the error message for exact location. Common causes: missing colons, quotes, or indentation.",
        "unused_import": "Remove the import line, or add # noqa: F401 if import is needed for side effects.",
        "long_function": "Extract logical sections into smaller helper functions. Aim for < 50 lines.",
        "too_many_params": "Group related parameters into a config class or dict.",
        "todo_comment": "Either complete the work or track it in your issue tracker with a ticket reference.",
        "fixme_comment": "Resolve the bug immediately or create a high-priority issue to track it.",
        "line_too_long": "Break the line at a logical point, or use line continuation with backslash.",
        "trailing_whitespace": "Remove whitespace at the end of the line. Most editors can do this automatically.",
        "empty_file": "Add meaningful code to the file or delete if not needed.",
    }

    return tips.get(issue_type, "Review the issue location and apply appropriate fixes.")


# ─────────────────────────────────────────────────────────────────────────────
# TESTING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────


def validate_all_issues(issues: List[Dict]) -> Tuple[int, int, List[str]]:
    """
    Validate a batch of issues and return statistics.

    Args:
        issues: List of issue dicts

    Returns:
        (total_valid, total_invalid, list_of_errors)
    """
    valid_count = 0
    invalid_count = 0
    errors = []

    for i, issue in enumerate(issues):
        is_valid, validation_errors = validate_issue(issue)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            for error in validation_errors:
                errors.append(f"Issue {i}: {error}")

    return valid_count, invalid_count, errors


def test_normalization() -> None:
    """Self-test to verify normalization works correctly."""
    print("Testing data normalization...")

    # Test 1: Scanner-style issue
    raw_issue = {
        "file": "/tmp/test.py",
        "line": 42,
        "issue_type": "unused_import",
        "severity": "warning",
        "description": "Import 'os' is never used",
        "fixable": True,
    }

    normalized = normalize_issue(raw_issue)
    assert normalized["file"] == "/tmp/test.py"
    assert normalized["line"] == 42
    assert normalized["issue_type"] == "unused_import"
    assert normalized["type"] == "unused_import"
    assert normalized["icon"] == "🟡"
    assert normalized["fixable"] is True
    print("  ✓ Test 1: Scanner-style issue normalization passed")

    # Test 2: Missing fields
    minimal_issue = {"file": "test.py"}
    normalized = normalize_issue(minimal_issue)
    assert "issue_type" in normalized
    assert "severity" in normalized
    assert "icon" in normalized
    print("  ✓ Test 2: Minimal issue normalization passed")

    # Test 3: None input
    normalized = normalize_issue(None)
    assert isinstance(normalized, dict)
    assert "file" in normalized
    print("  ✓ Test 3: None input handling passed")

    # Test 4: Batch normalization
    raw_issues = [raw_issue, minimal_issue]
    normalized_batch = normalize_scan_results(raw_issues)
    assert len(normalized_batch) == 2
    assert all("icon" in issue for issue in normalized_batch)
    print("  ✓ Test 4: Batch normalization passed")

    # Test 5: Validation
    is_valid, errors = validate_issue(normalized)
    assert is_valid
    print("  ✓ Test 5: Validation passed")

    print("✅ All normalization tests passed!")
