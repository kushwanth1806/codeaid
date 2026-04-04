# codeAID – AI Repository Debugger 🔍

An intelligent, agentic AI-powered repository debugger that automatically scans, analyzes, repairs, and explains code issues across multiple programming languages.

## Features ✨

- **🤖 Automated Code Scanning** – Detects syntax errors, unused imports, code quality issues
- **🔧 Intelligent Repair** – Automatically fixes common code issues
- **✅ Verification** – Validates repairs are correct
- **🧠 AI-Powered Explanations** – Detailed explanations using Claude AI (optional)
- **📊 Project Understanding** – Analyzes project architecture and structure
- **🌐 Flexible Input** – Analyze from GitHub repositories or ZIP files
- **📈 Visual Dashboard** – Beautiful Streamlit-based UI with metrics and reports
- **🌍 Multi-Language** – Supports Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP, and more

## Quick Start 🚀

### 1. Install

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup (Optional: LLM Integration)

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### 3. Run

```bash
streamlit run app.py
```

Open: `http://localhost:8501`

## Usage 📖

1. **Input**: Paste GitHub URL or upload ZIP file
2. **Analyze**: Click "Scan Repository" and wait for results
3. **Results**: View issues, suggested repairs, and explanations
4. **Metrics**: See code quality analysis and architecture overview

## Pipeline Components

| Component | Purpose |
|-----------|---------|
| **Scanner** | Detects issues via AST analysis |
| **Repair** | Automatically fixes common problems |
| **Verifier** | Validates repairs don't break code |
| **Explain** | Generates human-readable explanations |
| **Analyzer** | Multi-language code analysis |
| **LLM Agent** | Optional AI-enhanced insights |

## Architecture

```
codeaid/
├── app.py                  # Streamlit UI
├── core/
│   ├── agents/             # Pipeline agents
│   ├── repo_loader.py      # Repository loading
│   └── data_validation.py  # Data normalization
├── utils/                  # Utilities
├── static/                 # Assets
└── requirements.txt        # Dependencies
```

## Supported Languages 🌍

Primary: Python, JavaScript, TypeScript  
Secondary: Java, Go, Rust, C#, Ruby, PHP, Swift, Kotlin, Scala, R, Shell, SQL

## Performance ⚡

- Small projects (< 10 files): ~5 seconds
- Medium projects (10-100 files): ~15 seconds
- Large projects (100+ files): ~45 seconds

## License 📄

MIT License

## Contributing 🤝

Contributions welcome! Feel free to submit pull requests.

---

**Made with ❤️ for better code quality**
