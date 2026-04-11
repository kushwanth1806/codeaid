# codeAID – AI-Powered Repository Debugger & Auto-Repair Assistant

**Intelligent code analysis meets automatic bug fixing.** codeAID combines advanced static analysis with AI-powered insights to identify, repair, and explain code issues across multiple programming languages.

## 🎯 Overview

codeAID is a full-stack application that analyzes source code repositories to:
- **Scan** for bugs, style issues, and code quality problems
- **Repair** fixable issues automatically (unused imports, trailing whitespace, etc.)
- **Verify** that repairs don't break existing functionality
- **Analyze** project architecture and code quality metrics
- **Explain** issues with actionable insights
- **Export** repaired code for safe deployment

### Key Features
- ✅ **Multi-language support**: Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, C#, and more
- ✅ **Automatic repairs**: Safe, deterministic fixes for common code issues
- ✅ **Side-by-side comparison**: See original and fixed code with syntax highlighting
- ✅ **Copy-paste ready**: One-click code copying for manual review
- ✅ **AI insights**: Optional LLM integration for detailed analysis
- ✅ **Interactive dashboard**: React-based web UI with real-time results
- ✅ **REST API**: Full programmatic integration support

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ and npm
- Git

### Installation

```bash
# Clone repository
git clone <repository-url>
cd codeaid

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# or
.venv\Scripts\activate             # Windows

# Install Python dependencies
pip install -r requirements.txt

# Set up frontend
cd frontend && npm install && cd ..

# (Optional) Configure LLM for AI insights
export ANTHROPIC_API_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

### Running the Application

```bash
# Automated startup (recommended)
bash start.sh

# Or manual startup
# Terminal 1 - Backend:
source .venv/bin/activate && python api.py

# Terminal 2 - Frontend:
cd frontend && npm run dev
```

Open **http://localhost:3000** in your browser.

## 📊 Architecture

### Backend (Flask API)
- **Port**: 5001 (available at `http://localhost:5001`)
- **Modules**:
  - `api.py` - REST API endpoints
  - `core/agents/` - Analysis pipeline (scan, repair, verify, explain, analyze)
  - `core/repo_loader.py` - Repository loading (GitHub/ZIP)
  - `core/data_validation.py` - Input/output validation
  - `utils/` - Utility functions and metrics

### Frontend (React + Vite)
- **Port**: 3000
- **Components**:
  - Dashboard - Main analysis interface
  - Analysis - Results with code comparison
  - Overview - Project metrics and insights
  - Sidebar - Configuration and controls

### Data Flow
```
Input (GitHub URL / ZIP)
    ↓
Load Repository
    ↓
Scan (Issue Detection)
    ↓
Repair (Auto-fixes)
    ↓
Verify (Validation)
    ↓
Explain & Analyze
    ↓
Results Dashboard
```

## 📁 Project Structure

```
codeaid/
├── api.py                           # Flask REST API
├── start.sh                         # Startup script
├── requirements.txt                 # Python dependencies
├── .env.example                     # Configuration template
│
├── core/
│   ├── repo_loader.py               # Repository loading
│   ├── lang_detector.py             # Language detection
│   ├── data_validation.py           # Data validation
│   ├── error_handling.py            # Error handling
│   ├── api_validation.py            # API validation
│   └── agents/
│       ├── coordinator.py           # Pipeline orchestration
│       ├── scanner.py               # Issue detection
│       ├── repair.py                # Auto repairs
│       ├── verifier.py              # Repair verification
│       ├── explain.py               # Issue explanations
│       ├── project_understanding.py # Architecture analysis
│       ├── llm_agent.py             # AI integration (optional)
│       ├── export.py                # Code export
│       └── universal_analyzer.py    # Multi-language analyzer
│
├── utils/
│   ├── metrics.py                   # Code quality metrics
│   └── codexglue_loader.py          # Evaluation utilities
│
├── frontend/                        # React.js frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.jsx
│   │   ├── components/
│   │   └── styles/
│   └── package.json
│
└── tests/                           # Pytest test suite
    ├── test_agents_multilang.py
    ├── test_api.py
    ├── test_features.py
    ├── test_integration.py
    └── test_new_features.py
```

## 🔌 API Endpoints

### Health & Status
```
GET  /api/health           Health check
GET  /api/status           Configuration status
```

### Analysis
```
POST /api/analyze/github   Analyze GitHub repository
POST /api/analyze/upload   Analyze uploaded files
POST /api/overview         Get project overview
GET  /api/eval/codexglue   Run CodeXGLUE evaluation
```

### Example Requests

```bash
# Analyze GitHub repo
curl -X POST http://localhost:5001/api/analyze/github \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/username/repo",
    "use_llm": false
  }'

# Check API status
curl http://localhost:5001/api/status
```

## 🌍 Supported Languages

**Full Support**: Python, JavaScript, TypeScript, Java, Go, Rust  
**Partial Support**: C#, Ruby, PHP, Swift, Kotlin, Scala, R, Shell, SQL

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_api.py -v

# Run with coverage
python -m pytest tests/ --cov=core
```

## ⚙️ Configuration

### Environment Variables

```bash
# Optional: LLM Integration
ANTHROPIC_API_KEY=your-key          # For Claude AI
OPENAI_API_KEY=your-key             # For OpenAI GPT
LLM_PROVIDER=anthropic              # or 'openai'

# Recommended: Flask Settings
FLASK_ENV=production                # or 'development'
FLASK_DEBUG=0                       # Always 0 in production
```

See `.env.example` for a configuration template.

## 🔒 Security Best Practices

- **Never commit API keys** - use `.env` file (in .gitignore)
- **Use environment variables** for all sensitive data
- **Validate all inputs** - endpoints check URL format, file size, content-type
- **Enable HTTPS in production** - use reverse proxy (nginx/Cloudflare)
- **Test before deploying** - Run `python -m pytest tests/`
- **Review dependencies** - `pip list` and check for security updates

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill process
lsof -i :5001  # or :3000
kill -9 <PID>
```

### Python Module Import Errors
```bash
# Ensure you're in project root and venv is activated
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend Not Loading
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install && npm run dev
```

### LLM API Errors
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test connection
python -c "import anthropic; print('✓ SDK loaded')"
```

## 📈 Performance

| Operation | Time |
|-----------|------|
| Repository Scan | 0.5-2s |
| Auto Repair | 0.2-1s |
| Verification | 0.1-0.5s |
| LLM Analysis | 2-5s |
| **Total (no LLM)** | **1-3s** |
| **Total (with LLM)** | **3-8s** |

*Benchmarks for small-to-medium projects (50-500 files)*

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run `python -m pytest tests/` before submitting
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 💡 What's Next?

- Deploy to production with Docker
- Integrate with CI/CD pipelines
- Add support for more programming languages
- Implement advanced caching for performance
- Build team collaboration features

---

**Questions?** Open an issue or check the troubleshooting section above.
