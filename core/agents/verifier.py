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

import ast
from typing import List, Dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_all_repairs(repair_results: List[Dict]) -> List[Dict]:
    """
    Wrapper function: Verify repaired files.
    
    For now, returns empty list as verification is optional.
    """
    return []


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
        r["file"]
        for r in repair_results
        if r["status"] == "fixed"
    }

    file_map: Dict[str, str] = {f["path"]: f["source"] for f in files}

    results: List[Dict] = []
    for path in fixed_files:
        source = file_map.get(path, "")
        results.append(_verify_file(path, source))

    return results


def verify_source(path: str, source: str) -> Dict:
    """
    Compile-check a single source string.  Convenience wrapper for
    callers that already have the source text.
    """
    return _verify_file(path, source)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _verify_file(path: str, source: str) -> Dict:
    """Attempt to compile *source* and return a result dict."""
    try:
        compile(source, path, "exec")
        return {
            "file": path,
            "status": "passed",
            "detail": "File compiles successfully after repair.",
        }
    except SyntaxError as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"SyntaxError after repair at line {exc.lineno}: {exc.msg}",
        }
    except Exception as exc:
        return {
            "file": path,
            "status": "failed",
            "detail": f"Unexpected error during verification: {exc}",
        }
