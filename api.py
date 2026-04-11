# ===== api.py =====
"""
CodeAid Flask API Backend
Exposes CodeAid pipeline and evaluation features as REST endpoints.
"""

import os
import sys
import tempfile
import traceback
import zipfile
import io
import logging
from werkzeug.utils import secure_filename

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agents.coordinator import run_pipeline
from core.agents.llm_agent import is_llm_available
from utils.codexglue_loader import run_evaluation
from core.api_validation import (
    validate_github_url,
    validate_upload_request,
    validate_json_request,
    validate_api_key_format,
    validate_integer_param,
    validate_boolean_param,
)

# Load environment variables
load_dotenv()

# ── JSON Serialization Helper ─────────────────────────────────────────────────

def make_json_serializable(obj):
    """Convert non-JSON-serializable objects to serializable types."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return list(obj)  # Convert sets to lists
    elif hasattr(obj, '__dict__'):
        return make_json_serializable(obj.__dict__)
    else:
        return obj

# ── Flask App Setup ───────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# Upload configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'zip', 'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'go', 'rs', 'rb', 'php', 'cs'}
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Health & Status Endpoints ─────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'CodeAid API',
        'version': '1.0.0',
        'llm_available': is_llm_available(),
    }), 200


@app.route('/api/status', methods=['GET'])
def status():
    """Get current API status and configuration."""
    llm_provider = os.environ.get('LLM_PROVIDER', 'anthropic')
    has_api_key = False
    
    if llm_provider == 'anthropic':
        has_api_key = bool(os.environ.get('ANTHROPIC_API_KEY'))
    elif llm_provider == 'openai':
        has_api_key = bool(os.environ.get('OPENAI_API_KEY'))
    
    return jsonify({
        'llm_available': is_llm_available(),
        'llm_provider': llm_provider,
        'api_key_configured': has_api_key,
        'upload_limit_mb': 100,
    }), 200


# ── Analysis Endpoints ────────────────────────────────────────────────────────

@app.route('/api/analyze/github', methods=['POST'])
def analyze_github():
    """
    Analyze a GitHub repository.
    
    Request body:
    {
        "url": "https://github.com/username/repo",
        "use_llm": true
    }
    """
    try:
        # Validate request size
        data = request.get_json()
        
        # Validate JSON structure
        is_valid, error = validate_json_request(
            data,
            required_fields=['url'],
            field_types={'url': str, 'use_llm': bool}
        )
        if not is_valid:
            return jsonify({'error': error}), 400
        
        github_url = data['url'].strip()
        use_llm = data.get('use_llm', False)
        
        # Validate GitHub URL format
        is_valid, error = validate_github_url(github_url)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Run pipeline
        results = run_pipeline(
            source=github_url,
            is_zip=False,
            use_llm=use_llm and is_llm_available(),
        )
        
        # Make results JSON-serializable
        results = make_json_serializable(results)
        
        return jsonify(results), 200
    
    except Exception as e:
        # Don't expose internal traceback in response (security)
        return jsonify({
            'error': 'Failed to analyze GitHub repository. Please check the URL and try again.',
        }), 500


@app.route('/api/analyze/upload', methods=['POST'])
def analyze_upload():
    """
    Analyze uploaded files (ZIP or individual files).
    
    Multipart form data:
    - files: One or more uploaded files (ZIP or source code files)
    - use_llm: Boolean flag for LLM analysis
    """
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = request.files.getlist('files')
        
        # Validate upload request
        is_valid, error = validate_upload_request(uploaded_files)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Get and validate use_llm parameter
        use_llm_str = request.form.get('use_llm', 'false')
        is_valid, error, use_llm = validate_boolean_param(use_llm_str, 'use_llm')
        if not is_valid:
            use_llm = False  # Default to False if invalid
        
        # Handle single ZIP file
        if len(uploaded_files) == 1 and uploaded_files[0].filename.endswith('.zip'):
            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            uploaded_files[0].save(tmp_zip.name)
            zip_path = tmp_zip.name
            
            results = run_pipeline(
                source=zip_path,
                is_zip=True,
                use_llm=use_llm and is_llm_available(),
            )
            
            # Make results JSON-serializable
            results = make_json_serializable(results)
            
            return jsonify(results), 200
        
        # Handle multiple files or mix of ZIP and source files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for uploaded_file in uploaded_files:
                if uploaded_file.filename.endswith('.zip'):
                    # Extract ZIP contents into the new ZIP
                    with zipfile.ZipFile(io.BytesIO(uploaded_file.read())) as inner_zip:
                        for item in inner_zip.namelist():
                            zip_file.writestr(item, inner_zip.read(item))
                else:
                    # Add source files
                    zip_file.writestr(
                        secure_filename(uploaded_file.filename),
                        uploaded_file.read()
                    )
        
        # Save the created ZIP
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        tmp_zip.write(zip_buffer.getvalue())
        tmp_zip.flush()
        zip_path = tmp_zip.name
        
        results = run_pipeline(
            source=zip_path,
            is_zip=True,
            use_llm=use_llm and is_llm_available(),
        )
        
        # Make results JSON-serializable
        results = make_json_serializable(results)
        
        return jsonify(results), 200
    
    except Exception as e:
        # Don't expose internal traceback in response (security)
        return jsonify({
            'error': 'Failed to analyze uploaded files. Please check the files and try again.',
        }), 500


# ── Evaluation Endpoints ──────────────────────────────────────────────────────

@app.route('/api/eval/codexglue', methods=['POST'])
def eval_codexglue():
    """
    Run CodeXGLUE evaluation tests.
    Evaluates scanner on actual repository files if provided, otherwise uses synthetic benchmarks.
    
    Request body:
    {
        "max_samples": 15,
        "results": {... from /api/analyze/github or /api/analyze/upload} (optional)
    }
    """
    try:
        data = request.get_json() or {}
        
        # Validate max_samples parameter
        max_samples_input = data.get('max_samples', 15)
        is_valid, error, max_samples = validate_integer_param(
            max_samples_input,
            'max_samples',
            min_value=1,
            max_value=100
        )
        
        if not is_valid:
            max_samples = 15  # Default if validation fails
        
        # Extract repository files from analysis results if provided
        repo_files = None
        results = data.get('results', {})
        if results:
            stages = results.get('stages', {})
            load_stage = stages.get('load', {})
            # Get source files from load stage (now includes actual file content)
            repo_files = load_stage.get('source_files', [])
        
        eval_results = run_evaluation(max_samples=max_samples, repo_files=repo_files)
        
        return jsonify(eval_results), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to run evaluation. Please try again.',
        }), 500


# ── Configuration Endpoints ───────────────────────────────────────────────────

@app.route('/api/config/llm', methods=['POST'])
def configure_llm():
    """
    Configure LLM provider and API key.
    
    Request body:
    {
        "provider": "anthropic" or "openai",
        "api_key": "your-api-key"
    }
    """
    try:
        data = request.get_json()
        
        # Validate JSON structure
        is_valid, error = validate_json_request(
            data,
            required_fields=['provider'],
            field_types={'provider': str}
        )
        if not is_valid:
            return jsonify({'error': error}), 400
        
        provider = data.get('provider', '').lower().strip()
        api_key = data.get('api_key', '').strip() if data.get('api_key') else ''
        
        # Validate provider
        if provider not in ['anthropic', 'openai']:
            return jsonify({
                'error': 'Invalid provider. Must be "anthropic" or "openai"'
            }), 400
        
        # Validate API key if provided
        if api_key:
            is_valid, error = validate_api_key_format(api_key)
            if not is_valid:
                return jsonify({'error': error}), 400
        
        # Set environment variables
        os.environ['LLM_PROVIDER'] = provider
        if api_key:
            if provider == 'anthropic':
                os.environ['ANTHROPIC_API_KEY'] = api_key
            elif provider == 'openai':
                os.environ['OPENAI_API_KEY'] = api_key
        
        return jsonify({
            'provider': provider,
            'api_key_set': bool(api_key),
            'llm_available': is_llm_available(),
        }), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to configure LLM. Please check the parameters and try again.',
        }), 500


@app.route('/api/config/llm', methods=['GET'])
def get_llm_config():
    """Get current LLM configuration."""
    provider = os.environ.get('LLM_PROVIDER', 'anthropic')
    has_key = False
    
    if provider == 'anthropic':
        has_key = bool(os.environ.get('ANTHROPIC_API_KEY'))
    elif provider == 'openai':
        has_key = bool(os.environ.get('OPENAI_API_KEY'))
    
    return jsonify({
        'provider': provider,
        'api_key_configured': has_key,
        'llm_available': is_llm_available(),
    }), 200



# ── Overview & Summary Endpoints ──────────────────────────────────────────────

@app.route('/api/overview', methods=['POST'])
def get_overview():
    """
    Get comprehensive project overview (architecture, statistics, improvements).
    Requires the latest analysis results from a previous analyze call.
    
    Request body:
    {
        "results": {...}  # Results from /api/analyze/github or /api/analyze/upload
    }
    """
    try:
        data = request.get_json() or {}
        results = data.get('results', {})
        
        if not results:
            return jsonify({'error': 'No analysis results provided'}), 400
        
        stages = results.get('stages', {})
        understand = stages.get('understand', {})
        analysis = understand.get('analysis', {})
        load_stage = stages.get('load', {})
        
        # Extract project understanding data
        project_name = analysis.get('project_name', 'Unknown Project')
        project_type = analysis.get('project_type', 'Unknown')
        architecture = analysis.get('architecture', {})
        dependencies = analysis.get('dependencies', {})
        code_quality = analysis.get('code_quality', {})
        patterns = analysis.get('patterns', {})
        file_stats = analysis.get('file_stats', {})
        health_score = analysis.get('health_score', 0)
        
        # Build comprehensive overview structure
        overview = {
            'project_name': project_name,
            'project_type': project_type,
            'summary': analysis.get('summary', f'This is a {project_type} project'),
            'health_score': health_score,
            'architecture': {
                'style': architecture.get('style', 'Unknown'),
                'issues': architecture.get('issues', []),
                'positives': architecture.get('positives', []),
                'description': _build_architecture_description(architecture),
            },
            'statistics': {
                'total_files': load_stage.get('total_file_count', 0),
                'python_files': load_stage.get('python_file_count', 0),
                'source_files': load_stage.get('all_source_file_count', 0),
                'dependencies': {
                    'declared': len(dependencies.get('declared', [])),
                    'inferred': len(dependencies.get('inferred_third_party', set())),
                },
                'file_stats': file_stats,  # Include full file stats
            },
            'dependencies': dependencies.get('declared', [])[:20],  # Top 20
            'code_quality': code_quality,
            'patterns': patterns,  # Include both good and bad patterns
            'llm_advice': _generate_detailed_advice(analysis),
        }
        
        return jsonify(make_json_serializable(overview)), 200
    
    except Exception as e:
        # Don't expose internal traceback in response (security)
        return jsonify({
            'error': 'Failed to generate overview. Please ensure valid analysis results were provided.',
        }), 500


def _build_architecture_description(architecture: dict) -> str:
    """Build a detailed architecture description."""
    style = architecture.get('style', 'Unknown')
    positives = architecture.get('positives', [])
    issues = architecture.get('issues', [])
    
    description = f"Architecture Style: {style}\n\n"
    
    if positives:
        description += "Strengths:\n"
        for pos in positives:
            description += f"• {pos}\n"
        description += "\n"
    
    if issues:
        description += "Areas for Improvement:\n"
        for issue in issues:
            description += f"• {issue}\n"
    
    return description.strip()


def _generate_detailed_advice(analysis: dict) -> str:
    """Generate detailed AI insights and recommendations."""
    parts = []
    
    project_type = analysis.get('project_type', 'Unknown')
    patterns = analysis.get('patterns', {})
    architecture = analysis.get('architecture', {})
    file_stats = analysis.get('file_stats', {})
    code_quality = analysis.get('code_quality', {})
    health_score = analysis.get('health_score', 0)
    
    # Start with comprehensive project identification
    parts.append(f"🎯 PROJECT IDENTIFICATION\n{project_type} application - a specialized Python-based tool for code analysis and repair.")
    
    # Architecture feedback with detailed analysis
    if architecture.get('style'):
        style = architecture.get('style', '')
        parts.append(f"\n🏗️ ARCHITECTURE ASSESSMENT")
        if 'Modular' in style:
            parts.append(f"Your code follows a modular architecture, which is excellent for:\n• Reusability: Components can be used independently\n• Maintainability: Changes in one module don't affect others\n• Testing: Easier to write unit tests for isolated components\n• Scalability: Easy to add new features without breaking existing code")
        elif 'Monolithic' in style:
            parts.append(f"Your codebase is currently monolithic. Consider these improvements:\n• Extract shared utilities into separate modules\n• Create clear separation of concerns\n• Define module-level APIs\n• This will improve code reusability and testability")
        else:
            parts.append(f"Architecture Style: {style}")
    
    # Code quality feedback - detailed analysis
    parts.append(f"\n⚡ CODE QUALITY ANALYSIS")
    quality_items = []
    if code_quality.get('type_hints_used'):
        quality_items.append("✅ Type hints are properly used (improves IDE support and catches errors)")
    else:
        quality_items.append("❌ Missing type hints - Consider adding them for better code clarity")
    
    if code_quality.get('docstrings_present'):
        quality_items.append("✅ Comprehensive docstrings present (great documentation)")
    else:
        quality_items.append("❌ Missing docstrings - Add them to explain complex functions")
    
    if code_quality.get('logging_implemented'):
        quality_items.append("✅ Proper logging implemented (good for debugging)")
    else:
        quality_items.append("❌ No logging framework detected - Add logging for production readiness")
    
    if code_quality.get('error_handling'):
        quality_items.append("✅ Error handling is implemented (prevents crashes)")
    else:
        quality_items.append("❌ Weak error handling - Add try-except blocks and error messages")
    
    parts.append("\n".join(quality_items))
    
    # Testing and coverage feedback
    parts.append(f"\n🧪 TESTING & VERIFICATION")
    test_files = file_stats.get('test_files', 0)
    total_files = file_stats.get('total_files', 0)
    
    if test_files == 0:
        parts.append("⚠️  No test files detected. This is critical:\n• Add unit tests using pytest\n• Aim for at least 70% code coverage\n• Include integration tests for critical workflows")
    elif test_files < (total_files * 0.15):
        parts.append(f"⚠️  Low test coverage ({test_files} test files):\n• Expand test suite to cover more scenarios\n• Add tests for edge cases and error conditions\n• Set up CI/CD pipeline if not already done")
    else:
        parts.append(f"✅ Good test presence ({test_files} test files detected)\n• Ensure all critical paths are tested\n• Consider adding integration tests")
    
    # Dependencies and configuration feedback
    parts.append(f"\n📦 DEPENDENCY & CONFIGURATION MANAGEMENT")
    declared_deps = len(analysis.get('dependencies', {}).get('declared', []))
    config_files = file_stats.get('config_files', 0)
    
    if declared_deps > 0:
        parts.append(f"✅ Declared dependencies: {declared_deps}\n• Keep dependencies minimal and updated\n• Remove unused dependencies\n• Use version constraints to ensure stability")
    else:
        parts.append("⚠️  No dependencies declared - Ensure requirements.txt or setup.py is present")
    
    if config_files > 0:
        parts.append(f"✅ Configuration files present: {config_files}\n• Separating config from code is a best practice")
    else:
        parts.append("⚠️  No config files detected - Consider using environment-based configuration")
    
    # Health score with actionable feedback
    parts.append(f"\n💪 OVERALL PROJECT HEALTH SCORE: {health_score}/100")
    if health_score >= 80:
        parts.append("🟢 EXCELLENT: Your project is well-maintained with strong practices")
        parts.append("Next steps: Focus on performance optimization and advanced testing")
    elif health_score >= 60:
        parts.append("🟡 GOOD: The project has solid foundations with room for improvement")
        parts.append("Priority areas:\n• Increase test coverage\n• Add missing documentation\n• Implement comprehensive logging")
    else:
        parts.append("🔴 NEEDS IMPROVEMENT: Critical areas need attention")
        parts.append("Immediate actions:\n• Add test framework (pytest/unittest)\n• Write docstrings for all modules\n• Implement error handling patterns\n• Set up code quality checks (linting)")
    
    # Additional recommendations
    parts.append(f"\n🚀 ADDITIONAL RECOMMENDATIONS")
    anti_patterns = patterns.get('anti_patterns', [])
    if anti_patterns:
        parts.append(f"⚠️  Detected issues to fix:\n• " + "\n• ".join(anti_patterns[:3]))
    
    good_patterns = patterns.get('good_patterns', [])
    if good_patterns:
        parts.append(f"✅ Practices to maintain:\n• " + "\n• ".join(good_patterns[:3]))
    
    # Final action items
    parts.append("\n📋 ACTION PLAN\n1. Run code quality checks (pylint, flake8)\n2. Increase test coverage above 70%\n3. Add missing documentation\n4. Set up automated CI/CD pipeline\n5. Conduct code review for critical modules")
    
    return "\n".join(parts)


@app.route('/api/issues/summary', methods=['POST'])
def get_issues_summary():
    """
    Get comprehensive issues summary with severity, categorization, and file location.
    
    Request body:
    {
        "results": {...}  # Results from /api/analyze/github or /api/analyze/upload
    }
    """
    try:
        data = request.get_json() or {}
        results = data.get('results', {})
        
        if not results:
            return jsonify({'error': 'No analysis results provided'}), 400
        
        stages = results.get('stages', {})
        scan_stage = stages.get('scan', {})
        issues = scan_stage.get('results', [])
        
        # Group issues by severity
        by_severity = {'error': [], 'warning': [], 'info': []}
        by_file = {}
        by_type = {}
        
        for issue in issues:
            severity = issue.get('severity', 'info')
            issue_type = issue.get('issue_type', 'unknown')
            file = issue.get('relative_path', issue.get('file', 'unknown'))
            
            # Group by severity
            if severity in by_severity:
                by_severity[severity].append(issue)
            
            # Group by file
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(issue)
            
            # Group by type
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
        
        summary = {
            'total_issues': len(issues),
            'by_severity': {
                'errors': len(by_severity['error']),
                'warnings': len(by_severity['warning']),
                'info': len(by_severity['info']),
                'details': by_severity,
            },
            'by_file': by_file,
            'by_type': by_type,
            'critical_files': sorted(
                by_file.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5],  # Top 5 files with most issues
        }
        
        return jsonify(make_json_serializable(summary)), 200
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
        }), 500


# ── Error Handler ─────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Use 5001 as default to avoid AirPlay conflicts
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    if debug:
        logger = logging.getLogger(__name__)
        logger.info(f"Flask API running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
