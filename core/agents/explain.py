"""
explain.py
----------
Explanation agent.

Maps each issue type to a human-friendly explanation that includes:
  - What the problem is
  - Why it matters
  - How to fix it (manual guidance)

This agent works entirely without an LLM; the llm_agent can optionally
enrich explanations with deeper context.
"""

from typing import List, Dict


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_EXPLANATIONS: Dict[str, Dict] = {
    "syntax_error": {
        "title": "Syntax Error",
        "why": (
            "Python cannot parse this file at all. Any code in this file will "
            "fail to import or execute. This must be fixed before anything else."
        ),
        "how": (
            "Read the error message carefully — it points to the exact line. "
            "Common causes: missing colons, mismatched brackets, invalid indentation."
        ),
    },
    "unused_import": {
        "title": "Unused Import",
        "why": (
            "Importing a module that is never used increases load time, wastes memory, "
            "and confuses readers about the file's actual dependencies. "
            "Linters like flake8/ruff will flag these as F401 errors."
        ),
        "how": (
            "Remove the import statement, or if the import is needed for side effects, "
            "add a comment:  # noqa: F401"
        ),
    },
    "long_function": {
        "title": "Long Function",
        "why": (
            "Functions longer than ~50 lines are hard to read, test, and maintain. "
            "They often violate the Single Responsibility Principle and are a sign "
            "that the function is doing too many things."
        ),
        "how": (
            "Extract logical sections into smaller, well-named helper functions. "
            "Aim for functions that fit on one screen and do exactly one thing."
        ),
    },
    "too_many_params": {
        "title": "Too Many Parameters",
        "why": (
            "Functions with many parameters are hard to call correctly and test. "
            "They usually signal that related data should be grouped together."
        ),
        "how": (
            "Group related parameters into a dataclass, TypedDict, or plain dict. "
            "Consider the Builder pattern for objects with many optional settings."
        ),
    },
    "todo_comment": {
        "title": "TODO / FIXME Comment",
        "why": (
            "Leftover TODO/FIXME annotations indicate incomplete or known-broken code. "
            "They accumulate over time and often represent real technical debt."
        ),
        "how": (
            "Either resolve the TODO immediately or track it in your issue tracker "
            "(GitHub Issues, Jira, etc.) with a proper ticket reference in the comment."
        ),
    },
}

_DEFAULT_EXPLANATION = {
    "title": "Code Issue",
    "why": "This pattern can reduce code quality or maintainability.",
    "how": "Review the flagged location and apply appropriate refactoring.",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_scan_results(issues: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Explain scan results and group by file.
    
    Takes a flat list of issues and returns a list of file results,
    each containing grouped issues with explanations.
    
    Returns:
      [
        {"relative_path": str, "issues": [...]},
        ...
      ]
    """
    # First, add explanations to all issues
    explained = explain_issues(issues)
    
    # Group by file (using relative_path if available for display)
    from collections import defaultdict
    grouped = defaultdict(list)
    for issue in explained:
        # Use relative_path if available (enriched from coordinator), else file
        path = issue.get("relative_path", issue.get("file", "unknown"))
        grouped[path].append(issue)
    
    # Return as list of file results
    return [
        {"relative_path": path, "issues": issues_list}
        for path, issues_list in grouped.items()
    ]


def explain_issues(issues: List[Dict]) -> List[Dict]:
    """
    Attach a human-readable explanation to every issue dict.

    Parameters
    ----------
    issues : list of issue dicts from scanner

    Returns
    -------
    Same list, each dict enriched with an "explanation" key:
      {
        "title": str,
        "why":   str,
        "how":   str,
      }
    """
    for issue in issues:
        tpl = _EXPLANATIONS.get(issue["issue_type"], _DEFAULT_EXPLANATION)
        issue["explanation"] = {
            "title": tpl["title"],
            "why": tpl["why"],
            "how": tpl["how"],
        }
    return issues


def get_explanation(issue_type: str) -> Dict:
    """Return the explanation template for a single issue type."""
    return _EXPLANATIONS.get(issue_type, _DEFAULT_EXPLANATION)
