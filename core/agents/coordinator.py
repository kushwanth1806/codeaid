# ===== agents/coordinator.py =====
"""
Coordinator Agent: Orchestrates the full CodeAid pipeline.
Acts as the single entry point for the Streamlit dashboard.
Manages agent interactions and aggregates all results.
"""

import time
from typing import Callable, Dict, List, Optional

from core.repo_loader import load_repository, cleanup_repo
from core.agents.scanner import scan_repository, summarize_scan
from core.agents.repair import repair_repository, summarize_repairs
from core.agents.verifier import verify_all_repairs, summarize_verification
from core.agents.explain import explain_scan_results
from core.agents.project_understanding import analyze_project, build_project_summary_text
from core.agents import llm_agent


def run_pipeline(
    source: str,
    is_zip: bool = False,
    use_llm: bool = False,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Dict:
    """
    Execute the full CodeAid analysis pipeline.

    Pipeline stages:
        1. Load repository (clone or extract)
        2. Scan all Python files for issues (AST analysis)
        3. Repair fixable issues (unused imports)
        4. Verify repairs compile correctly
        5. Explain all detected issues
        6. Understand project architecture
        7. (Optional) LLM-enhanced analysis

    Args:
        source: GitHub URL or path to ZIP file.
        is_zip: True if source is a ZIP file path.
        use_llm: If True and API key is set, enrich with LLM insights.
        progress_callback: Optional fn(stage_name, progress_0_to_1) for UI updates.

    Returns:
        Comprehensive results dict ready for dashboard rendering.
    """

    def _progress(stage: str, pct: float):
        if progress_callback:
            progress_callback(stage, pct)

    results = {
        "source": source,
        "is_zip": is_zip,
        "stages": {},
        "errors": [],
        "timings": {},
        "llm_available": llm_agent.is_llm_available(),
    }

    # ── Stage 1: Load Repository ──────────────────────────────────────────────
    _progress("Loading repository…", 0.05)
    t0 = time.time()
    try:
        repo_data = load_repository(source, is_zip=is_zip)
    except Exception as e:
        results["errors"].append(f"Repository loading failed: {e}")
        return results

    results["stages"]["load"] = {
        "repo_path": repo_data["repo_path"],
        "python_file_count": len(repo_data["python_files"]),
        "total_file_count": len(repo_data["all_files"]),
    }
    results["timings"]["load"] = round(time.time() - t0, 2)
    _progress("Repository loaded.", 0.15)

    # ── Stage 2: Scan ─────────────────────────────────────────────────────────
    _progress("Scanning files for issues…", 0.25)
    t0 = time.time()
    try:
        scan_results = scan_repository(repo_data["python_files"])
        scan_summary = summarize_scan(scan_results)
    except Exception as e:
        results["errors"].append(f"Scanning failed: {e}")
        cleanup_repo(repo_data["temp_dir"])
        return results

    results["stages"]["scan"] = {
        "results": scan_results,
        "summary": scan_summary,
    }
    results["timings"]["scan"] = round(time.time() - t0, 2)
    _progress("Scan complete.", 0.40)

    # ── Stage 3: Repair ───────────────────────────────────────────────────────
    _progress("Applying automatic repairs…", 0.50)
    t0 = time.time()
    try:
        repair_results = repair_repository(repo_data["python_files"], scan_results)
        repair_summary = summarize_repairs(repair_results)
    except Exception as e:
        results["errors"].append(f"Repair failed: {e}")
        repair_results = []
        repair_summary = {"files_changed": 0, "total_repairs": 0, "details": []}

    results["stages"]["repair"] = {
        "results": repair_results,
        "summary": repair_summary,
    }
    results["timings"]["repair"] = round(time.time() - t0, 2)
    _progress("Repairs applied.", 0.60)

    # ── Stage 4: Verify ───────────────────────────────────────────────────────
    _progress("Verifying repaired code…", 0.68)
    t0 = time.time()
    try:
        verification_results = verify_all_repairs(repair_results)
        verification_summary = summarize_verification(verification_results)
    except Exception as e:
        results["errors"].append(f"Verification failed: {e}")
        verification_results = []
        verification_summary = {"total_files": 0, "passed": 0, "failed": 0, "regressions": 0}

    results["stages"]["verify"] = {
        "results": verification_results,
        "summary": verification_summary,
    }
    results["timings"]["verify"] = round(time.time() - t0, 2)
    _progress("Verification complete.", 0.75)

    # ── Stage 5: Explain ──────────────────────────────────────────────────────
    _progress("Generating explanations…", 0.80)
    t0 = time.time()
    try:
        explained_results = explain_scan_results(scan_results)
    except Exception as e:
        results["errors"].append(f"Explanation generation failed: {e}")
        explained_results = scan_results

    results["stages"]["explain"] = {"results": explained_results}
    results["timings"]["explain"] = round(time.time() - t0, 2)
    _progress("Explanations generated.", 0.85)

    # ── Stage 6: Project Understanding ───────────────────────────────────────
    _progress("Analyzing project architecture…", 0.90)
    t0 = time.time()
    try:
        project_analysis = analyze_project(
            repo_data["all_files"], repo_data["repo_path"]
        )
        project_summary_text = build_project_summary_text(project_analysis)

        if use_llm and llm_agent.is_llm_available():
            llm_arch_advice = llm_agent.llm_analyze_architecture(project_summary_text)
        else:
            llm_arch_advice = None

        project_analysis["llm_advice"] = llm_arch_advice

    except Exception as e:
        results["errors"].append(f"Project understanding failed: {e}")
        project_analysis = {}

    results["stages"]["understand"] = {"analysis": project_analysis}
    results["timings"]["understand"] = round(time.time() - t0, 2)
    _progress("Analysis complete!", 1.0)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cleanup_repo(repo_data["temp_dir"])

    results["total_time"] = round(sum(results["timings"].values()), 2)
    return results


def get_all_issues_flat(results: Dict) -> List[Dict]:
    """
    Flatten all issues from explained_results into a single list.
    Each issue includes the file path for easy display.

    Returns:
        List of issue dicts with added 'file' key.
    """
    flat = []
    explained = results.get("stages", {}).get("explain", {}).get("results", [])
    for file_result in explained:
        for issue in file_result.get("issues", []):
            flat.append(
                {
                    **issue,
                    "file": file_result.get("relative_path", "unknown"),
                }
            )
    return flat
