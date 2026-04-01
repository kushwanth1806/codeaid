# ===== app.py =====
"""
CodeAid – Agentic AI Repository Debugger
Streamlit Dashboard: Main entry point.
"""

import os
import sys
import tempfile
import traceback

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agents.coordinator import run_pipeline, get_all_issues_flat
from core.agents.llm_agent import is_llm_available
from utils.codexglue_loader import run_evaluation


# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CodeAid – AI Repository Debugger",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { color: #e94560; font-size: 2.5rem; margin: 0; }
    .main-header p  { color: #a8b2d8; font-size: 1.1rem; margin: 0.5rem 0 0; }

    .metric-card {
        background: #1e1e2e;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #e94560; }
    .metric-card .label { font-size: 0.85rem; color: #888; margin-top: 4px; }

    .issue-card {
        border-left: 4px solid #e94560;
        background: #1a1a2e;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.6rem;
    }
    .issue-card.warning { border-left-color: #f39c12; }
    .issue-card.info    { border-left-color: #3498db; }
    .issue-card.critical{ border-left-color: #e74c3c; }

    .health-bar-container { background: #2d2d44; border-radius: 20px; height: 20px; }
    .health-bar { border-radius: 20px; height: 20px; transition: width 0.5s; }

    .tip-card {
        background: #0d2137;
        border: 1px solid #1a4a7a;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        color: #a8d8f0;
    }
    .good-pattern  { color: #2ecc71; }
    .bad-pattern   { color: #e74c3c; }
    .stage-badge {
        display: inline-block;
        background: #0f3460;
        color: #e94560;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper Functions ──────────────────────────────────────────────────────────

def _render_eval_tab():
    """Render the CodeXGLUE evaluation results."""
    eval_data = st.session_state.eval_results

    if eval_data is None:
        st.info("Click **Run CodeXGLUE Eval** in the sidebar to evaluate scanner accuracy.")
        return

    agg = eval_data.get("aggregate_metrics", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Samples Evaluated", eval_data.get("samples_evaluated", 0))
    col2.metric("Precision", f"{agg.get('precision', 0):.1%}")
    col3.metric("Recall", f"{agg.get('recall', 0):.1%}")
    col4.metric("F1 Score", f"{agg.get('f1', 0):.1%}")

    st.caption(f"**Dataset:** {eval_data.get('source', '')}")
    st.caption(
        f"TP: {eval_data.get('total_tp',0)} | "
        f"FP: {eval_data.get('total_fp',0)} | "
        f"FN: {eval_data.get('total_fn',0)}"
    )

    st.markdown("### Per-Sample Results")
    per_sample = eval_data.get("per_sample_results", [])
    if per_sample:
        rows = [
            {
                "ID": s["id"],
                "Description": s["description"],
                "GT Issues": len(s["ground_truth"]),
                "Detected": len(s["detected"]),
                "TP": s["tp"],
                "FP": s["fp"],
                "FN": s["fn"],
                "F1": f"{s['metrics']['f1']:.2f}",
            }
            for s in per_sample
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    input_mode = st.radio(
        "Repository Source",
        ["🔗 GitHub URL", "📦 ZIP Upload"],
        index=0,
    )

    github_url = ""
    zip_path = ""
    is_zip = False

    if input_mode == "🔗 GitHub URL":
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/username/repo",
            help="Public GitHub repository URL",
        )
    else:
        uploaded_file = st.file_uploader("Upload ZIP File", type=["zip"])
        if uploaded_file:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp.write(uploaded_file.read())
            tmp.flush()
            zip_path = tmp.name
            is_zip = True

    st.markdown("---")
    st.markdown("### 🤖 LLM Settings")

    # Provider selection
    llm_provider = st.selectbox(
        "LLM Provider",
        ["anthropic", "openai"],
        index=0,
        help="Choose your LLM provider",
    )
    os.environ["LLM_PROVIDER"] = llm_provider

    # API key input based on provider
    if llm_provider == "anthropic":
        api_key_input = st.text_input(
            "Anthropic API Key (optional)",
            type="password",
            placeholder="sk-ant-...",
            help="Leave blank to use heuristic-only mode",
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input
    elif llm_provider == "openai":
        api_key_input = st.text_input(
            "OpenAI API Key (optional)",
            type="password",
            placeholder="sk-...",
            help="Leave blank to use heuristic-only mode",
        )
        if api_key_input:
            os.environ["OPENAI_API_KEY"] = api_key_input
    else:
        api_key_input = None

    use_llm = st.checkbox(
        "Enable LLM Reasoning",
        value=bool(api_key_input),
        help="Uses LLM for deeper architectural analysis",
    )

    llm_status = "✅ Available" if is_llm_available() else "⚠️ Not configured"
    st.caption(f"LLM Status: {llm_status} ({llm_provider})")

    st.markdown("---")
    analyze_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.markdown("---")
    eval_btn = st.button("📊 Run CodeXGLUE Eval", use_container_width=True)

    st.markdown("---")
    st.markdown(
        """
        **Pipeline Stages**
        1. 📥 Load Repository
        2. 🔬 AST Scan
        3. 🔧 Auto-Repair
        4. ✅ Verify
        5. 💡 Explain
        6. 🏗️ Understand
        """
    )


# ── Session State ─────────────────────────────────────────────────────────────

if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None
if "eval_results" not in st.session_state:
    st.session_state.eval_results = None


# ── Run Analysis ──────────────────────────────────────────────────────────────

if analyze_btn:
    source = github_url.strip() if not is_zip else zip_path
    if not source:
        st.error("Please provide a GitHub URL or upload a ZIP file.")
    else:
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(stage: str, pct: float):
            progress_bar.progress(pct)
            status_text.markdown(f"⚡ **{stage}**")

        with st.spinner("Running CodeAid pipeline…"):
            try:
                results = run_pipeline(
                    source=source,
                    is_zip=is_zip,
                    use_llm=use_llm,
                    progress_callback=update_progress,
                )
                st.session_state.pipeline_results = results
                progress_bar.progress(1.0)
                status_text.success("✅ Analysis complete!")
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.code(traceback.format_exc())


# ── Run CodeXGLUE Eval ────────────────────────────────────────────────────────

if eval_btn:
    with st.spinner("Running CodeXGLUE evaluation…"):
        try:
            eval_results = run_evaluation(max_samples=15)
            st.session_state.eval_results = eval_results
        except Exception as e:
            st.error(f"Evaluation error: {e}")


# ── Main Dashboard ────────────────────────────────────────────────────────────

results = st.session_state.pipeline_results

if results:
    errors = results.get("errors", [])
    if errors:
        for err in errors:
            st.error(err)

    tabs = st.tabs([
        "📊 Overview",
        "🔬 Issues",
        "🔧 Repairs",
        "✅ Verification",
        "🏗️ Project Understanding",
        "📈 CodeXGLUE Eval",
        "⏱️ Timings",
    ])

    # ── Tab 0: Overview ───────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("## 📊 Analysis Overview")

        load_stage = results["stages"].get("load", {})
        scan_summary = results["stages"].get("scan", {}).get("summary", {})
        repair_summary = results["stages"].get("repair", {}).get("summary", {})
        verify_summary = results["stages"].get("verify", {}).get("summary", {})

        col1, col2, col3, col4, col5 = st.columns(5)
        metrics = [
            (col1, load_stage.get("python_file_count", 0), "Python Files"),
            (col2, scan_summary.get("total_issues", 0), "Issues Found"),
            (col3, scan_summary.get("severity_counts", {}).get("critical", 0), "Critical"),
            (col4, repair_summary.get("files_changed", 0), "Files Repaired"),
            (col5, verify_summary.get("pass_rate", 0), "Verify Pass %"),
        ]
        for col, val, label in metrics:
            with col:
                st.metric(label, val)

        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            issues_by_type = scan_summary.get("issues_by_type", {})
            if issues_by_type:
                fig = px.pie(
                    names=list(issues_by_type.keys()),
                    values=list(issues_by_type.values()),
                    title="Issues by Type",
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No issues detected.")

        with col_chart2:
            sev = scan_summary.get("severity_counts", {})
            if any(sev.values()):
                fig2 = go.Figure(
                    go.Bar(
                        x=list(sev.keys()),
                        y=list(sev.values()),
                        marker_color=["#e74c3c", "#f39c12", "#3498db"],
                    )
                )
                fig2.update_layout(
                    title="Issues by Severity",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    xaxis=dict(gridcolor="#333"),
                    yaxis=dict(gridcolor="#333"),
                )
                st.plotly_chart(fig2, use_container_width=True)

        # File list
        st.markdown("### 📁 Repository Files")
        scan_results = results["stages"].get("scan", {}).get("results", [])
        if scan_results:
            df = pd.DataFrame(
                [
                    {
                        "File": r["relative_path"],
                        "Issues": len(r["issues"]),
                        "Parsed": "✅" if r.get("parse_success") else "❌",
                    }
                    for r in scan_results
                ]
            )
            st.dataframe(df, use_container_width=True, height=300)

    # ── Tab 1: Issues ─────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("## 🔬 Detected Issues")

        all_issues = get_all_issues_flat(results)

        if not all_issues:
            st.success("🎉 No issues detected in this repository!")
        else:
            # Filters
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                severity_filter = st.multiselect(
                    "Severity",
                    ["critical", "warning", "info"],
                    default=["critical", "warning", "info"],
                )
            with col_f2:
                type_options = list({i["type"] for i in all_issues})
                type_filter = st.multiselect("Issue Type", type_options, default=type_options)
            with col_f3:
                file_options = list({i["file"] for i in all_issues})
                file_filter = st.multiselect("File", file_options, default=file_options)

            filtered = [
                i for i in all_issues
                if i.get("severity") in severity_filter
                and i.get("type") in type_filter
                and i.get("file") in file_filter
            ]

            st.caption(f"Showing {len(filtered)} of {len(all_issues)} issues")

            for issue in filtered:
                sev = issue.get("severity", "info")
                icon = issue.get("icon", "⚪")
                title = issue.get("title", issue.get("type", "Issue"))
                css_class = (
                    "critical" if sev == "critical"
                    else "warning" if sev == "warning"
                    else "info"
                )
                with st.expander(
                    f"{icon} [{sev.upper()}] {title} — `{issue['file']}` Line {issue.get('line', '?')}"
                ):
                    col_a, col_b = st.columns([1, 1])
                    with col_a:
                        st.markdown(f"**Message:** {issue.get('message', '')}")
                        st.markdown(f"**Fixable:** {'✅ Yes' if issue.get('fixable') else '❌ No'}")
                        if issue.get("snippet"):
                            st.code(issue["snippet"], language="python")
                    with col_b:
                        st.markdown(f"**Summary:** {issue.get('summary', '')}")
                        st.markdown(f"**Impact:** {issue.get('impact', '')}")
                        st.info(f"💡 **Tip:** {issue.get('tip', '')}")

    # ── Tab 2: Repairs ────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("## 🔧 Automatic Repairs")

        repair_results = results["stages"].get("repair", {}).get("results", [])
        repair_summary = results["stages"].get("repair", {}).get("summary", {})

        col1, col2 = st.columns(2)
        col1.metric("Files Changed", repair_summary.get("files_changed", 0))
        col2.metric("Total Repairs", repair_summary.get("total_repairs", 0))

        changed = [r for r in repair_results if r.get("changed")]
        if not changed:
            st.info("No automatic repairs were applied (no fixable issues found).")
        else:
            for repair in changed:
                with st.expander(f"🔧 {repair['relative_path']}"):
                    for rep in repair.get("repairs_applied", []):
                        st.success(f"✅ {rep}")

                    col_orig, col_fixed = st.columns(2)
                    with col_orig:
                        st.markdown("**Original:**")
                        st.code(repair["original_content"][:1000], language="python")
                    with col_fixed:
                        st.markdown("**Repaired:**")
                        st.code(repair["repaired_content"][:1000], language="python")

    # ── Tab 3: Verification ───────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("## ✅ Repair Verification")

        verify_results = results["stages"].get("verify", {}).get("results", [])
        verify_summary = results["stages"].get("verify", {}).get("summary", {})

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Files", verify_summary.get("total_files", 0))
        col2.metric("✅ Passed", verify_summary.get("passed", 0))
        col3.metric("❌ Failed", verify_summary.get("failed", 0))
        col4.metric("⚠️ Regressions", verify_summary.get("regressions", 0))

        changed_verifs = [v for v in verify_results if v.get("changed")]
        if changed_verifs:
            st.markdown("### Changed File Verification")
            for v in changed_verifs:
                icon = "✅" if v["repaired_valid"] else "❌"
                reg = " ⚠️ REGRESSION" if v.get("regression") else ""
                with st.expander(f"{icon} {v['relative_path']}{reg}"):
                    st.markdown(f"- **Original valid:** {'✅' if v['original_valid'] else '❌'}")
                    st.markdown(f"- **Repaired valid:** {'✅' if v['repaired_valid'] else '❌'}")
                    if v.get("verification_error"):
                        st.error(f"Error: {v['verification_error']}")
                    for rep in v.get("repairs_applied", []):
                        st.success(f"Applied: {rep}")
        else:
            st.info("No files were modified — nothing to verify.")

    # ── Tab 4: Project Understanding ──────────────────────────────────────────
    with tabs[4]:
        st.markdown("## 🏗️ Project Understanding")

        analysis = results["stages"].get("understand", {}).get("analysis", {})
        if not analysis:
            st.warning("Project understanding analysis was not available.")
        else:
            # Health Score
            health = analysis.get("health_score", 0)
            health_color = (
                "#2ecc71" if health >= 70
                else "#f39c12" if health >= 40
                else "#e74c3c"
            )
            st.markdown(f"### 🏥 Project Health Score: **{health}/100**")
            st.markdown(
                f"""
                <div class="health-bar-container">
                    <div class="health-bar" style="width:{health}%; background:{health_color};"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("")

            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown("### 🎯 Project Identity")
                st.info(f"**Type:** {analysis.get('project_type', 'Unknown')}")

                arch = analysis.get("architecture", {})
                st.info(f"**Architecture:** {arch.get('style', 'Unknown')}")

                stats = analysis.get("file_stats", {})
                st.markdown("**Repository Statistics:**")
                stat_df = pd.DataFrame(
                    list(stats.items()), columns=["Metric", "Value"]
                )
                st.dataframe(stat_df, hide_index=True, use_container_width=True)

                # Dependencies
                deps = analysis.get("dependencies", {})
                declared = deps.get("declared", [])
                if declared:
                    st.markdown(f"**Declared Dependencies ({len(declared)}):**")
                    st.code(", ".join(declared))

            with col_r:
                st.markdown("### 🔍 Architecture Assessment")

                positives = arch.get("positives", [])
                issues_arch = arch.get("issues", [])

                if positives:
                    st.markdown("**✅ Good Practices:**")
                    for p in positives:
                        st.success(p)

                if issues_arch:
                    st.markdown("**⚠️ Architecture Issues:**")
                    for issue in issues_arch:
                        st.warning(issue)

            st.markdown("---")
            col_pat, col_perf = st.columns(2)

            with col_pat:
                st.markdown("### 🧩 Design Patterns")
                patterns = analysis.get("patterns", {})

                for p in patterns.get("good_patterns", []):
                    st.markdown(f"<span class='good-pattern'>✅ {p}</span>", unsafe_allow_html=True)
                for p in patterns.get("anti_patterns", []):
                    st.markdown(f"<span class='bad-pattern'>❌ {p}</span>", unsafe_allow_html=True)

                if not patterns.get("good_patterns") and not patterns.get("anti_patterns"):
                    st.info("No notable patterns detected.")

            with col_perf:
                st.markdown("### ⚡ Performance Hints")
                for hint in analysis.get("performance_hints", []):
                    st.warning(hint)
                if not analysis.get("performance_hints"):
                    st.success("No obvious performance issues detected.")

            st.markdown("---")
            st.markdown("### 💡 Developer Tips")
            tip_cols = st.columns(2)
            tips = analysis.get("developer_tips", [])
            for i, tip in enumerate(tips):
                with tip_cols[i % 2]:
                    st.markdown(
                        f"<div class='tip-card'>💡 {tip}</div>",
                        unsafe_allow_html=True,
                    )

            # LLM Architectural Advice
            llm_advice = analysis.get("llm_advice")
            if llm_advice:
                st.markdown("---")
                st.markdown("### 🤖 LLM Architectural Analysis")
                st.markdown(llm_advice)

    # ── Tab 5: CodeXGLUE Eval ─────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("## 📈 CodeXGLUE Evaluation")
        _render_eval_tab()

    # ── Tab 6: Timings ────────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown("## ⏱️ Pipeline Timings")
        timings = results.get("timings", {})
        if timings:
            fig = go.Figure(
                go.Bar(
                    x=list(timings.values()),
                    y=list(timings.keys()),
                    orientation="h",
                    marker_color="#e94560",
                )
            )
            fig.update_layout(
                title="Time per Stage (seconds)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(gridcolor="#333"),
                yaxis=dict(gridcolor="#333"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Total Analysis Time", f"{results.get('total_time', 0):.2f}s")


# ── Standalone Mode ───────────────────────────────────────────────────────────

# Show eval even without a full pipeline run
if not results and st.session_state.eval_results:
    st.markdown("---")
    st.markdown("## 📈 CodeXGLUE Evaluation Results")
    _render_eval_tab()


# ── Landing State ─────────────────────────────────────────────────────────────

if not results and not st.session_state.eval_results:
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 2rem; color: #666;">
            <h2 style="color:#e94560;">Ready to Analyze</h2>
            <p style="font-size:1.1rem;">
                Enter a GitHub repository URL in the sidebar and click <strong>Run Analysis</strong>.<br>
                Or run the <strong>CodeXGLUE Evaluation</strong> to benchmark the scanner.
            </p>
            <br>
            <p style="color:#444;">
                <strong>Pipeline:</strong>
                📥 Load → 🔬 Scan → 🔧 Repair → ✅ Verify → 💡 Explain → 🏗️ Understand
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
