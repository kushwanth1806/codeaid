# ===== app.py =====
"""
CodeAid – Agentic AI Repository Debugger
Streamlit Dashboard: Main entry point.
"""

import os
import sys
import tempfile
import traceback
import zipfile
import io
from collections import defaultdict

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
    page_title="codeAID – AI Repository Debugger",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    :root {
        --primary: #ffffff;
        --secondary: #0d47a1;
        --accent: #0ea5a5;
        --success: #059669;
        --warning: #d97706;
        --danger: #dc2626;
        --info: #0284c7;
        --light: #f9fafb;
        --border: #e5e7eb;
        --text-primary: #111827;
        --text-secondary: #6b7280;
        --bg-primary: #ffffff;
        --bg-secondary: #f3f4f6;
        --bg-tertiary: #ede9fe;
        --accent-subtle: #e0f2fe;
        --sidebar-bg: #fafbfc;
    }

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body, html {
        background: #ffffff;
    }

    /* Main Header - Clean and Minimal (GitHub/Linear Style) */
    .main-header {
        background: linear-gradient(135deg, #ffffff 0%, var(--bg-secondary) 100%);
        padding: 3rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2.5rem;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 2rem;
        margin-bottom: 0;
        position: relative;
        z-index: 1;
    }
    
    .logo-image {
        width: 100px;
        height: 100px;
        object-fit: contain;
        image-rendering: high-quality;
        flex-shrink: 0;
        filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.08));
    }
    
    .header-text {
        flex: 1;
        text-align: center;
    }
    
    .main-header h1 {
        color: var(--text-primary);
        font-size: 2.6rem;
        margin: 0.5rem 0 0.8rem 0;
        font-weight: 800;
        letter-spacing: -0.8px;
        position: relative;
        z-index: 1;
        background: linear-gradient(135deg, #111827 0%, #0ea5a5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header p {
        color: var(--text-secondary);
        font-size: 0.95rem;
        margin: 0.7rem 0 0;
        position: relative;
        z-index: 1;
        font-weight: 500;
        line-height: 1.5;
    }
    
    .main-header .subtitle {
        color: var(--accent);
        font-size: 0.85rem;
        margin-top: 0.6rem;
        position: relative;
        z-index: 1;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Metric Cards */
    .metric-card {
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.75rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    
    .metric-card:hover {
        border-color: var(--accent);
        background: var(--accent-subtle);
        box-shadow: 0 4px 12px rgba(14, 165, 165, 0.12);
        transform: translateY(-2px);
    }
    
    .metric-card .value {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--accent);
        display: block;
        margin-bottom: 0.6rem;
    }
    
    .metric-card .label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-weight: 700;
    }

    /* Issue Cards */
    .issue-card {
        border-left: 4px solid var(--accent);
        background: var(--bg-primary);
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
        transition: all 0.3s ease;
        border: 1px solid var(--border);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    
    .issue-card:hover {
        background: var(--accent-subtle);
        border-color: var(--accent);
        box-shadow: 0 4px 12px rgba(14, 165, 165, 0.1);
        transform: translateX(4px);
    }
    
    .issue-card.warning {
        border-left-color: var(--warning);
    }
    
    .issue-card.warning:hover {
        background: rgba(217, 119, 6, 0.06);
        border-color: var(--warning);
    }
    
    .issue-card.info {
        border-left-color: var(--info);
    }
    
    .issue-card.info:hover {
        background: rgba(2, 132, 199, 0.06);
        border-color: var(--info);
    }
    
    .issue-card.success {
        border-left-color: var(--success);
    }
    
    .issue-card.success:hover {
        background: rgba(5, 150, 105, 0.06);
        border-color: var(--success);
    }

    /* Progress Bar */
    .health-bar-container {
        background: var(--bg-secondary);
        border-radius: 12px;
        height: 28px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    
    .health-bar {
        border-radius: 12px;
        height: 28px;
        transition: width 0.8s ease;
        background: linear-gradient(90deg, #059669 0%, #d97706 50%, #dc2626 100%);
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    /* Info Cards */
    .tip-card {
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        color: var(--text-secondary);
        transition: all 0.3s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    
    .tip-card:hover {
        border-color: var(--accent);
        background: var(--accent-subtle);
        box-shadow: 0 2px 8px rgba(14, 165, 165, 0.08);
    }

    /* Status Indicators */
    .good-pattern { color: var(--success); font-weight: 600; }
    .bad-pattern { color: var(--danger); font-weight: 600; }
    .neutral-pattern { color: var(--info); font-weight: 600; }

    /* Badges */
    .stage-badge {
        display: inline-block;
        background: var(--accent-subtle);
        color: var(--accent);
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        margin-right: 6px;
        border: 1px solid rgba(14, 165, 165, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.6px;
        transition: all 0.2s ease;
    }
    
    .stage-badge:hover {
        background: var(--accent);
        color: white;
    }

    /* Tabs and Sections */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid var(--border);
        background: transparent;
    }
    
    .stTabs [role="tablist"] [role="tab"] {
        background: transparent;
        border-color: transparent;
        color: var(--text-secondary);
        padding: 12px 18px;
        font-weight: 600;
        border-bottom: 3px solid transparent;
        transition: all 0.3s ease;
        font-size: 0.95rem;
    }
    
    .stTabs [role="tablist"] [role="tab"]:hover {
        color: var(--accent);
    }
    
    .stTabs [role="tablist"] [role="tab"][aria-selected="true"] {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 14px 16px;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
        font-weight: 600;
    }
    
    .streamlit-expanderHeader:hover {
        background: var(--accent-subtle);
        border-color: var(--accent);
    }

    /* Code Blocks */
    pre {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        padding: 16px !important;
        color: var(--text-secondary) !important;
        line-height: 1.6 !important;
    }
    
    code {
        color: #0284c7 !important;
        font-family: 'Monaco', 'Menlo', 'Courier New', monospace !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    /* Buttons */
    .stButton > button {
        background: var(--accent);
        color: white;
        border: none;
        padding: 10px 22px;
        border-radius: 8px;
        font-weight: 700;
        transition: all 0.3s ease;
        text-transform: capitalize;
        letter-spacing: 0px;
        font-size: 0.9rem;
        box-shadow: 0 2px 4px rgba(14, 165, 165, 0.15);
    }
    
    .stButton > button:hover {
        background: #0d8c8c;
        box-shadow: 0 4px 12px rgba(14, 165, 165, 0.3);
        transform: translateY(-1px);
    }
    
    .stButton > button:active {
        background: #067878;
        transform: translateY(0px);
    }

    /* Inputs */
    .stSelectbox > div > div {
        background: var(--bg-primary);
        border: 1px solid var(--border);
        color: var(--text-primary);
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: var(--accent);
        background: var(--accent-subtle);
    }
    
    .stTextInput > div > div > input {
        background: var(--bg-primary) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 165, 0.1) !important;
    }

    /* Messages */
    .stSuccess {
        background: rgba(5, 150, 105, 0.08);
        border-left: 4px solid var(--success);
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(5, 150, 105, 0.25);
    }
    
    .stWarning {
        background: rgba(217, 119, 6, 0.08);
        border-left: 4px solid var(--warning);
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(217, 119, 6, 0.25);
    }
    
    .stError {
        background: rgba(220, 38, 38, 0.08);
        border-left: 4px solid var(--danger);
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(220, 38, 38, 0.25);
    }
    
    .stInfo {
        background: rgba(2, 132, 199, 0.08);
        border-left: 4px solid var(--info);
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(2, 132, 199, 0.25);
    }

    /* Section Headers */
    .section-header {
        border-bottom: 2px solid var(--border);
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
        color: var(--text-primary);
        font-weight: 700;
        font-size: 1.3rem;
        letter-spacing: -0.3px;
    }

    /* Typography */
    h1 { color: var(--text-primary); font-weight: 800; letter-spacing: -0.6px; }
    h2 { color: var(--text-primary); font-weight: 700; letter-spacing: -0.3px; }
    h3 { color: var(--text-primary); font-weight: 700; }
    p { color: var(--text-secondary); line-height: 1.6; font-weight: 500; }
    
    /* Status Indicators */
    .good-pattern { color: var(--success); font-weight: 700; }
    .bad-pattern { color: var(--danger); font-weight: 700; }
    .neutral-pattern { color: var(--accent); font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper Functions ──────────────────────────────────────────────────────────

def get_corrected_code_suggestion(issue: dict, source_code_snippet: str = None) -> str:
    """
    Generate corrected code suggestion for skipped issues.
    
    Args:
        issue: Issue dict with type, line, etc
        source_code_snippet: Original code snippet if available
        
    Returns:
        Suggested corrected code as string
    """
    issue_type = issue.get("issue_type", "unknown")
    
    if issue_type == "line_too_long":
        # For line_too_long, suggest line breaking strategies
        return """# Suggested improvements for line too long:

# Option 1: Break into multiple lines at logical operators
# Before:
# const result = someFunction(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9);

# After:
const result = someFunction(
    arg1, arg2, arg3, arg4, arg5,
    arg6, arg7, arg8, arg9
);

# Option 2: Extract to intermediate variables
# Before:
# const finalValue = complexCalculation(parameter1, parameter2, parameter3, parameter4);

# After:
const intermediate1 = complexCalculation(parameter1, parameter2);
const finalValue = someOtherFunction(intermediate1, parameter3, parameter4);

# Option 3: Use helper functions or method calls
# Before:
# output = very_long_function_name(arg1, arg2, arg3) and another_long_function(arg4, arg5)

# After:
firstCondition = very_long_function_name(arg1, arg2, arg3)
secondCondition = another_long_function(arg4, arg5)
output = firstCondition and secondCondition
"""
    
    elif issue_type == "trailing_whitespace":
        return """# Remove trailing whitespace from the end of lines
# Before:
x = 5   
y = 10  

# After:
x = 5
y = 10
"""
    
    elif issue_type == "unused_import":
        return """# Remove unused import statements
# Before:
import os
import sys
import json  # unused

def main():
    print(sys.version)

# After:
import sys

def main():
    print(sys.version)
"""
    
    else:
        return f"Suggested fix for {issue_type}: Review code at line {issue.get('line', '?')} and refactor appropriately."

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
    # Display logo image
    logo_path = "static/codeAID.jpeg"
    
    try:
        if os.path.exists(logo_path):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo_path, width=180)
        else:
            st.warning(f"⚠️ Logo not found at {logo_path}")
    except Exception as e:
        st.error(f"Failed to load logo: {str(e)}")
    
    st.markdown("")  # Add spacing
    
    # Sidebar Logo/Branding
    st.markdown(
        """
        <style>
        .sidebar-header {
            text-align: center;
            padding: 1.2rem 0 1.8rem 0;
            margin-bottom: 1.8rem;
            border-bottom: 2px solid var(--border);
        }
        .sidebar-header h2 {
            margin: 0.5rem 0 0;
            color: var(--text-primary);
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: -0.4px;
            background: linear-gradient(135deg, #111827 0%, #0ea5a5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .sidebar-header p {
            margin: 0.4rem 0 0;
            color: var(--text-secondary);
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.4px;
        }
        </style>
        <div class='sidebar-header'>
            <h2>codeAID</h2>
            <p>Configuration</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("## Configuration")

    input_mode = st.radio(
        "Choose Source",
        ["GitHub URL", "ZIP Upload"],
        index=0,
    )

    github_url = ""
    zip_path = ""
    is_zip = False

    if input_mode == "GitHub URL":
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/username/repo",
            help="Public GitHub repository URL",
        )
    else:
        st.markdown("#### Upload Files")
        st.caption(
            "**Option 1:** Upload a single ZIP file containing your entire project folder\n\n"
            "**Option 2:** Select multiple Python files from your project (preserves folder structure)"
        )
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=["zip", "py"],
            accept_multiple_files=True,
            help="Upload ZIP file(s) or individual Python files"
        )
        
        if uploaded_files:
            # Handle ZIP files and multiple file uploads
            tmp_dir = tempfile.mkdtemp()
            
            # Check if we have a single ZIP file
            if len(uploaded_files) == 1 and uploaded_files[0].name.endswith(".zip"):
                # Single ZIP file - extract it
                tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                tmp_zip.write(uploaded_files[0].read())
                tmp_zip.flush()
                zip_path = tmp_zip.name
                is_zip = True
            else:
                # Multiple files or mix of ZIP and PY files - create a ZIP from them
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name.endswith(".zip"):
                            # Extract ZIP contents into the new ZIP
                            with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue())) as inner_zip:
                                for item in inner_zip.namelist():
                                    zip_file.writestr(item, inner_zip.read(item))
                        else:
                            # Add Python files maintaining relative paths
                            zip_file.writestr(uploaded_file.name, uploaded_file.getvalue())
                
                # Save the created ZIP
                tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                tmp_zip.write(zip_buffer.getvalue())
                tmp_zip.flush()
                zip_path = tmp_zip.name
                is_zip = True
            
            st.success(f"Loaded {len(uploaded_files)} file(s)")

    st.markdown("---")
    st.markdown("### LLM Settings")

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

    llm_status = "Available" if is_llm_available() else "Not configured"
    st.caption(f"LLM Status: {llm_status} ({llm_provider})")

    st.markdown("---")
    
    # Network connectivity check (for GitHub URL mode)
    if input_mode == "GitHub URL":
        if st.button("Check GitHub Connectivity", use_container_width=True):
            import socket
            try:
                socket.create_connection(("github.com", 443), timeout=3)
                st.success("GitHub is reachable")
            except (socket.timeout, socket.gaierror, ConnectionRefusedError):
                st.error(
                    "Cannot reach GitHub\n\n"
                    "Solutions:\n"
                    "• Check your internet connection\n"
                    "• Try using a ZIP file instead\n"
                    "• Check firewall/proxy settings"
                )

    st.markdown("---")
    analyze_btn = st.button("Run Analysis", type="primary", use_container_width=True)

    st.markdown("---")
    eval_btn = st.button("Run CodeXGLUE Eval", use_container_width=True)

    st.markdown("---")
    st.markdown(
        """
        **Pipeline Stages**
        1. Load Repository
        2. AST Scan
        3. Auto-Repair
        4. Verify
        5. Explain
        6. Project Understanding
        """
    )

    st.markdown("---")
    st.markdown(
        """
        **🌍 Multi-Language Support**
        
        codeAID analyzes projects in:
        - 🐍 Python
        - 📜 JavaScript/TypeScript
        - ☕ Java
        - 🟦 C#
        - 🐹 Go
        - 🦀 Rust
        - 💎 Ruby
        - 🐘 PHP
        - And more!
        
        File format: Any programming language source files
        """
    )


# ── Session State ─────────────────────────────────────────────────────────────

if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None
if "eval_results" not in st.session_state:
    st.session_state.eval_results = None


# ── Main Content ─────────────────────────────────────────────────────────────

# Render main header in the main content area
st.markdown(
    """<div class='main-header'>
        <div class='header-text'>
            <h1>codeAID</h1>
            <p>AI-Powered Repository Debugger & Auto-Repair Assistant</p>
            <p class='subtitle'>Scan • Analyze • Fix • Verify</p>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

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
            status_text.markdown(f"**{stage}**")

        with st.spinner("Running codeAID pipeline…"):
            try:
                results = run_pipeline(
                    source=source,
                    is_zip=is_zip,
                    use_llm=use_llm,
                    progress_callback=update_progress,
                )
                st.session_state.pipeline_results = results
                progress_bar.progress(1.0)
                status_text.success("Analysis complete!")
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
            # Enhanced error display with better formatting
            error_text = str(err)
            
            # Check for network-related errors
            if "network" in error_text.lower() or "could not resolve" in error_text.lower():
                st.error(f"**Network Error**\n\n{error_text}")
                st.info(
                    "**Troubleshooting Tips:**\n\n"
                    "1. **Check Internet Connection**: Ensure you have internet access\n"
                    "2. **Use ZIP Instead**: Download the repo as ZIP and upload it\n"
                    "3. **Check Firewall**: Your network may be blocking GitHub\n"
                    "4. **Try Again**: Temporary network issues can occur"
                )
            elif "not found" in error_text.lower() or "authentication" in error_text.lower():
                st.error(f"**Repository Error**\n\n{error_text}")
                st.info(
                    "**Try These:**\n\n"
                    "1. Verify the GitHub URL is correct\n"
                    "2. Ensure the repository is public\n"
                    "3. Upload a ZIP file instead"
                )
            else:
                st.error(error_text)

    tabs = st.tabs([
        "Overview",
        "Issues",
        "Repairs",
        "Verification",
        "Project Understanding",
        "CodeXGLUE Eval",
        "Timings",
    ])

    # ── Tab 0: Overview ───────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("## Analysis Overview")

        load_stage = results["stages"].get("load", {})
        scan_summary = results["stages"].get("scan", {}).get("summary", {})
        repair_summary = results["stages"].get("repair", {}).get("summary", {})
        verify_summary = results["stages"].get("verify", {}).get("summary", {})

        col1, col2, col3, col4, col5 = st.columns(5)
        metrics = [
            (col1, load_stage.get("all_source_file_count", load_stage.get("python_file_count", 0)), "Source Files"),
            (col2, scan_summary.get("total_issues", 0), "Issues Found"),
            (col3, repair_summary.get("total_repairs", 0), "Issues Fixed"),
            (col4, repair_summary.get("files_changed", 0), "Files Changed"),
            (col5, load_stage.get("total_file_count", 0), "Total Files"),
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
        # Use explained results which are grouped by file
        explained_results = results["stages"].get("explain", {}).get("results", [])
        if explained_results:
            df = pd.DataFrame(
                [
                    {
                        "File": r.get("relative_path", "unknown"),
                        "Issues": len(r.get("issues", [])),
                        "Parsed": "✓",  # If we have issues, parsing succeeded
                    }
                    for r in explained_results
                ]
            )
            st.dataframe(df, use_container_width=True, height=300)
        else:
            st.info("No files analyzed yet.")

    # ── Tab 1: Issues ─────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("## 🔬 Detected Issues")

        all_issues = get_all_issues_flat(results)

        if not all_issues:
            st.success("No issues detected in this repository!")
        else:
            # Filters
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                severity_filter = st.multiselect(
                    "Severity",
                    ["critical", "error", "warning", "info", "note"],
                    default=["critical", "error", "warning"],
                )
            with col_f2:
                # FIX: Use .get() to safely extract type field
                type_options = list({i.get("type") or i.get("issue_type") or "unknown" for i in all_issues})
                type_options = sorted([t for t in type_options if t])  # Remove None, sort
                type_filter = st.multiselect("Issue Type", type_options, default=type_options)
            with col_f3:
                # FIX: Use .get() for file path
                file_options = list({i.get("file") or i.get("path") or "unknown" for i in all_issues})
                file_options = sorted([f for f in file_options if f])  # Remove None, sort
                file_filter = st.multiselect("File", file_options, default=file_options)

            # FIX: Use safe .get() for filtering
            filtered = [
                i for i in all_issues
                if (i.get("severity") or i.get("level") or "info") in severity_filter
                and (i.get("type") or i.get("issue_type") or "unknown") in type_filter
                and (i.get("file") or i.get("path") or "unknown") in file_filter
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
                # Use safe .get() for file and line fields
                file_path = issue.get("file") or issue.get("path", "unknown")
                line_num = issue.get("line", "?")
                with st.expander(
                    f"{icon} [{sev.upper()}] {title} — `{file_path}` Line {line_num}"
                ):
                    col_a, col_b = st.columns([1, 1])
                    with col_a:
                        st.markdown(f"**Message:** {issue.get('message', '')}")
                        st.markdown(f"**Fixable:** {'Yes' if issue.get('fixable') else 'No'}")
                        if issue.get("snippet"):
                            st.code(issue.get("snippet", ""), language="python")
                    with col_b:
                        st.markdown(f"**Summary:** {issue.get('summary', '')}")
                        st.markdown(f"**Impact:** {issue.get('impact', '')}")
                        st.info(f"**Tip:** {issue.get('tip', '')}")

    # ── Tab 2: Repairs ────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("## Automatic Repairs")

        repair_results = results["stages"].get("repair", {}).get("results", [])
        repair_summary = results["stages"].get("repair", {}).get("summary", {})

        col1, col2, col3 = st.columns(3)
        col1.metric("Files Changed", repair_summary.get("files_changed", 0))
        col2.metric("Issues Fixed", repair_summary.get("total_repairs", 0))
        col3.metric("Issues Skipped", len([r for r in repair_results if r.get("status") == "skipped"]))

        # Filter repairs by status
        fixed_repairs = [r for r in repair_results if r.get("status") == "fixed"]
        skipped_repairs = [r for r in repair_results if r.get("status") == "skipped"]
        failed_repairs = [r for r in repair_results if r.get("status") == "failed"]
        
        # Show fixed repairs
        if fixed_repairs:
            st.markdown("### Successful Repairs")
            repairs_by_file = defaultdict(list)
            for repair in fixed_repairs:
                file_path = repair.get("relative_path", repair.get("file", "unknown"))
                repairs_by_file[file_path].append(repair)
            
            for file_path, file_repairs in sorted(repairs_by_file.items()):
                with st.expander(f"{file_path} ({len(file_repairs)} fixed)"):
                    for repair in file_repairs:
                        st.success(f"{repair.get('detail', 'Issue fixed')}")
        else:
            st.info("No automatic repairs were applied.")
        
        # Show skipped repairs (not auto-fixable)
        if skipped_repairs:
            st.markdown("### Skipped (Not Auto-Fixable)")
            st.info(
                "These issues were detected but cannot be automatically fixed. "
                "Here's the corrected code you can manually copy and paste:"
            )
            
            # Group skipped by reason
            skipped_by_reason = defaultdict(list)
            for skip in skipped_repairs:
                reason = skip.get("detail", "Unknown reason")
                skipped_by_reason[reason].append(skip)
            
            for reason, items in sorted(skipped_by_reason.items()):
                with st.expander(f"{reason} ({len(items)} issues)"):
                    for item in items:
                        issue_type = item.get("issue_type", "unknown")
                        file_path = item.get("relative_path", item.get("file", "unknown"))
                        line_no = item.get("line", "?")
                        
                        st.warning(f"**{issue_type}** at `{file_path}:{line_no}`")
                        
                        # Show corrected code suggestions
                        corrected_code = get_corrected_code_suggestion(item)
                        st.markdown("**Suggested Fix (Copy & Paste):**")
                        st.code(corrected_code, language="python" if ".py" in file_path else "javascript")
                        
                        # Add a separator between items
                        st.markdown("---")
        
        # Show failed repairs
        if failed_repairs:
            st.markdown("### Failed Repairs")
            for fail in failed_repairs:
                issue_type = fail.get("issue_type", "unknown")
                file_path = fail.get("relative_path", fail.get("file", "unknown"))
                line_no = fail.get("line", "?")
                detail = fail.get("detail", "Unknown error")
                st.error(f"**{issue_type}** at `{file_path}:{line_no}`: {detail}")

    # ── Tab 3: Verification ───────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("## Repair Verification")

        verify_results = results["stages"].get("verify", {}).get("results", [])
        verify_summary = results["stages"].get("verify", {}).get("summary", {})

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Files", verify_summary.get("total_files", 0))
        col2.metric("Passed", verify_summary.get("passed", 0))
        col3.metric("Failed", verify_summary.get("failed", 0))
        col4.metric("Regressions", verify_summary.get("regressions", 0))

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
