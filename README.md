# CodeAid – AI Repository Debugger 🔍

An intelligent, agentic AI-powered repository debugger that automatically scans, analyzes, repairs, and explains code issues in Python projects. CodeAid combines static code analysis with AI-driven insights to help you maintain high-quality codebases.

## Features ✨

- **🤖 Automated Code Scanning** – Detects syntax errors, unused imports, code quality issues using AST analysis
- **🔧 Intelligent Repair** – Automatically fixes common issues like unused imports and logical problems
- **✅ Verification** – Validates that repairs don't introduce new issues
- **🧠 AI-Powered Explanations** – Detailed explanations of detected issues and their impact
- **📊 Project Understanding** – Analyzes project architecture and code structure
- **🌐 Flexible Input** – Analyze code from GitHub repositories or local ZIP files
- **📈 Visual Dashboard** – Beautiful Streamlit-based UI with metrics, charts, and detailed reports
- **🚀 Optional LLM Integration** – Enhanced analysis using Claude AI (Anthropic)

## Architecture 🏗️

```
CodeAid/
├── core/
│   ├── repo_loader.py           # Clone/extract repositories
│   ├── agents/
│   │   ├── coordinator.py        # Orchestrates the pipeline
│   │   ├── scanner.py            # Detects code issues
│   │   ├── repair.py             # Fixes detected issues
│   │   ├── verifier.py           # Validates repairs
│   │   ├── explain.py            # Explains issues in natural language
│   │   ├── project_understanding.py  # Analyzes project structure
│   │   └── llm_agent.py          # LLM integration (Claude)
├── utils/
│   ├── codexglue_loader.py      # Code evaluation utilities
│   └── metrics.py               # Performance metrics
├── app.py                       # Streamlit dashboard
└── requirements.txt             # Dependencies
```

## Installation 🛠️

### Prerequisites
- Python 3.8+
- Git
- pip

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/kushwanth1806/codeaid.git
   cd codeaid
   ```

2. **Create a Virtual Environment** (Optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up API Keys** (Optional for LLM features)
   ```bash
   export ANTHROPIC_API_KEY='your-anthropic-api-key-here'
   ```

## Usage 🚀

### Running the Dashboard

Start the Streamlit application:

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

### How to Use

1. **Select Input Source**
   - **GitHub Repository**: Enter a repository URL (e.g., `https://github.com/username/repo`)
   - **Local ZIP File**: Upload a ZIP file containing your project

2. **Configuration Options**
   - Enable/Disable LLM Analysis (requires ANTHROPIC_API_KEY)
   - Choose analysis depth and verbosity

3. **Run Analysis Pipeline**
   - The pipeline executes sequentially:
     1. Repository loading
     2. Code scanning
     3. Issue repair
     4. Verification
     5. Explanation generation
     6. Project understanding

4. **View Results**
   - **Issues Tab**: Detailed list of all detected issues
   - **Repairs Tab**: Summary of applied fixes
   - **Verification Tab**: Status of repair validation
   - **Metrics Tab**: Code quality metrics and statistics
   - **Project Overview**: Architecture and structure analysis

## Core Components 📦

### 1. Scanner Agent
- **Purpose**: Detects code issues using AST analysis
- **Detects**:
  - Syntax errors
  - Unused imports and variables
  - Undefined names
  - Code complexity issues
  - Style violations

### 2. Repair Agent
- **Purpose**: Automatically fixes detected issues
- **Fixes**:
  - Remove unused imports
  - Fix import order
  - Resolve undefined references
  - Code formatting

### 3. Verifier Agent
- **Purpose**: Validates that repairs are correct
- **Checks**:
  - Syntax correctness after repairs
  - No regression in code functionality
  - Proper execution of fixed code

### 4. Explain Agent
- **Purpose**: Generates human-readable explanations
- **Provides**:
  - Issue descriptions
  - Impact analysis
  - Recommended fixes
  - Best practices

### 5. Project Understanding Agent
- **Purpose**: Analyzes overall project structure
- **Analyzes**:
  - Module dependencies
  - Project complexity
  - Architecture patterns
  - Code organization

### 6. LLM Agent (Optional)
- **Purpose**: Enhanced analysis using AI
- **Integrates**: Anthropic's Claude API
- **Provides**:
  - Deep code analysis
  - Context-aware explanations
  - Intelligent repair suggestions

## Configuration ⚙️

### Environment Variables

```bash
# LLM Integration
ANTHROPIC_API_KEY=your-api-key-here

# Optional: Customize behavior
CODEAID_TEMP_DIR=/path/to/temp  # Temporary directory for repo extraction
```

### Dependencies

- **streamlit** (>=1.32.0) – Web framework for dashboard
- **anthropic** (>=0.25.0) – Claude API integration
- **requests** (>=2.31.0) – HTTP requests
- **gitpython** (>=3.1.41) – Git repository operations
- **radon** (>=6.0.1) – Code complexity metrics
- **pyflakes** (>=3.2.0) – Python linter
- **datasets** (>=2.18.0) – Dataset loading
- **pandas** (>=2.2.0) – Data manipulation
- **plotly** (>=5.20.0) – Interactive visualizations
- **pygments** (>=2.17.2) – Code syntax highlighting

## Example Workflows 📋

### Analyze a GitHub Repository
```bash
# Visit the dashboard at localhost:8501
# 1. Paste URL: https://github.com/username/repo-name
# 2. Click "Analyze Repository"
# 3. Wait for pipeline completion
# 4. Review results in the dashboard
```

### Analyze Local Project
```bash
# 1. Zip your project: zip -r project.zip ./my-project
# 2. Upload via dashboard
# 3. Choose analysis options
# 4. Review findings
```

### Get AI-Enhanced Analysis
```bash
# 1. Set ANTHROPIC_API_KEY environment variable
# 2. Enable "Use LLM Analysis" in dashboard
# 3. Run normal analysis
# 4. Get detailed AI explanations for each issue
```

## Output & Reports 📊

The dashboard provides:

- **Issue Summary**: Count and types of issues found
- **Repair Status**: Number of issues fixed and verification results
- **Code Metrics**: Complexity, maintainability, and quality scores
- **Visual Charts**: Issue distribution, severity levels, file breakdown
- **Detailed Logs**: Execution traces and intermediate results

## Performance 🚄

- **Small Projects** (<1MB): ~10-30 seconds
- **Medium Projects** (1-50MB): ~1-5 minutes
- **Large Projects** (50+MB): ~5-15 minutes

*Times vary based on code complexity and LLM usage*

## Limitations ⚠️

- Currently supports **Python files only**
- Requires valid Python syntax to analyze (broken syntax stops some checks)
- LLM features require valid ANTHROPIC_API_KEY
- Large repositories may require significant time/resources

## Contributing 🤝

Contributions are welcome! Areas for improvement:

- Support for additional languages (JavaScript, Java, etc.)
- Enhanced repair capabilities
- Performance optimizations
- Additional analysis agents
- Better visualization options

## Troubleshooting 🔧

### Issue: "Module not found" errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: LLM features not working
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# If not set:
export ANTHROPIC_API_KEY='your-key-here'
```

### Issue: Repository clone fails
- Check internet connection
- Verify GitHub repository URL is correct
- For private repos, ensure SSH keys are configured

### Issue: Streamlit not starting
```bash
# Try specifying port explicitly
streamlit run app.py --server.port 8501
```

## License 📄

This project is provided as-is for educational and development purposes.

## Support 💬

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review pipeline logs for debugging

---

**Made with ❤️ for better code quality**

Happy debugging! 🚀
