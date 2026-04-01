# ===== agents/project_understanding.py =====
"""
Project Understanding Agent: Analyzes repository structure holistically.
Identifies project type, architecture, dependencies, and design quality.
Uses heuristics + optional LLM reasoning.
"""

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Project Type Detection ────────────────────────────────────────────────────

_PROJECT_SIGNATURES = {
    "FastAPI / Flask API": [
        r"from fastapi", r"import fastapi", r"from flask", r"import flask",
        r"@app\.route", r"@router\.", r"uvicorn\.run",
    ],
    "Django Web App": [
        r"django\.setup", r"from django", r"INSTALLED_APPS", r"urlpatterns",
    ],
    "Machine Learning / Data Science": [
        r"import torch", r"import tensorflow", r"from sklearn", r"import keras",
        r"import pandas", r"import numpy", r"model\.fit", r"\.predict\(",
    ],
    "CLI Tool / Script": [
        r"argparse", r"click", r"typer", r"if __name__.*__main__",
        r"sys\.argv",
    ],
    "Data Pipeline / ETL": [
        r"airflow", r"prefect", r"luigi", r"dask", r"spark",
        r"\.read_csv\(", r"\.to_csv\(",
    ],
    "Testing Suite": [
        r"import pytest", r"import unittest", r"def test_", r"class Test",
    ],
    "Package / Library": [
        r"setup\.py", r"pyproject\.toml", r"setup\.cfg",
        r"__all__\s*=", r"from \. import",
    ],
}


def detect_project_type(all_files: List[Dict]) -> Tuple[str, List[str]]:
    """
    Identify the most likely project type from file contents.

    Returns:
        (project_type_string, list_of_matched_signals)
    """
    scores: Dict[str, int] = defaultdict(int)
    signals: Dict[str, List[str]] = defaultdict(list)

    combined_content = "\n".join(
        f["content"] for f in all_files if f["extension"] in {".py", ".toml", ".cfg"}
    )

    for project_type, patterns in _PROJECT_SIGNATURES.items():
        for pattern in patterns:
            if re.search(pattern, combined_content, re.IGNORECASE):
                scores[project_type] += 1
                signals[project_type].append(pattern)

    if not scores:
        return "General Python Project", []

    best = max(scores, key=scores.get)
    return best, signals[best]


# ── Dependency Analysis ───────────────────────────────────────────────────────

def extract_dependencies(all_files: List[Dict]) -> Dict:
    """
    Parse requirements.txt, pyproject.toml, and import statements
    to identify project dependencies.

    Returns:
        Dict with: declared (list), inferred_third_party (set), std_lib_usage (set).
    """
    declared = []
    inferred = set()

    # From requirements files
    for f in all_files:
        if f["name"] in ("requirements.txt", "requirements-dev.txt"):
            for line in f["content"].splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg = re.split(r"[>=<!\[]", line)[0].strip()
                    if pkg:
                        declared.append(pkg)

        if f["name"] == "pyproject.toml":
            matches = re.findall(r'"([a-zA-Z0-9_\-]+)\s*[>=<]', f["content"])
            declared.extend(matches)

    # From import statements in Python files
    std_lib = {
        "os", "sys", "re", "io", "json", "math", "time", "datetime",
        "pathlib", "typing", "collections", "itertools", "functools",
        "abc", "copy", "random", "hashlib", "logging", "threading",
        "subprocess", "shutil", "tempfile", "glob", "ast", "inspect",
        "unittest", "dataclasses", "enum", "contextlib", "traceback",
    }

    third_party = set()
    for f in all_files:
        if f["extension"] != ".py":
            continue
        for match in re.finditer(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", f["content"], re.MULTILINE):
            pkg = match.group(1)
            if pkg not in std_lib:
                third_party.add(pkg)

    return {
        "declared": list(set(declared)),
        "inferred_third_party": third_party,
        "std_lib_usage": std_lib & third_party,  # intersection = potential confusion
    }


# ── Architecture Assessment ───────────────────────────────────────────────────

def assess_architecture(all_files: List[Dict], repo_path: str) -> Dict:
    """
    Evaluate structural quality of the repository.

    Returns:
        Dict with: style (str), issues (list), positives (list).
    """
    py_files = [f for f in all_files if f["extension"] == ".py"]
    root_py = [f for f in py_files if "/" not in f["relative_path"].replace("\\", "/")]
    has_packages = any(f["name"] == "__init__.py" for f in all_files)
    has_tests = any("test" in f["relative_path"].lower() for f in all_files)
    has_readme = any(f["name"].lower() in ("readme.md", "readme.rst", "readme.txt") for f in all_files)
    has_requirements = any("requirements" in f["name"].lower() for f in all_files)
    has_config = any(f["name"] in ("pyproject.toml", "setup.py", "setup.cfg") for f in all_files)
    has_ci = any(".github" in f["relative_path"] or "ci" in f["name"].lower() for f in all_files)
    has_dockerfile = any("dockerfile" in f["name"].lower() for f in all_files)
    has_env_example = any(".env.example" in f["name"].lower() for f in all_files)

    issues = []
    positives = []

    # Architecture style
    if has_packages and len(py_files) > 5:
        style = "Modular (Package-based)"
        positives.append("Code is organized into packages with __init__.py files.")
    elif len(root_py) > len(py_files) * 0.7:
        style = "Monolithic (Flat file structure)"
        issues.append("Most code is in the root directory — consider organizing into modules/packages.")
    else:
        style = "Mixed / Transitional"

    # Test coverage indicator
    if has_tests:
        positives.append("Test files detected — good practice!")
    else:
        issues.append("No test files detected. Add pytest or unittest tests.")

    # Documentation
    if has_readme:
        positives.append("README file present — project is documented.")
    else:
        issues.append("No README found. Add a README.md with project description and setup instructions.")

    # Dependency management
    if has_requirements or has_config:
        positives.append("Dependency file found (requirements.txt or pyproject.toml).")
    else:
        issues.append("No dependency management file found (requirements.txt or pyproject.toml).")

    # CI/CD
    if has_ci:
        positives.append("CI/CD configuration detected.")
    else:
        issues.append("No CI/CD pipeline detected. Consider adding GitHub Actions or similar.")

    # Docker
    if has_dockerfile:
        positives.append("Dockerfile found — project is containerization-ready.")

    # Secrets management
    if has_env_example:
        positives.append(".env.example found — environment variables are documented.")
    else:
        issues.append("No .env.example file. Document environment variables to prevent secrets leakage.")

    return {
        "style": style,
        "issues": issues,
        "positives": positives,
    }


# ── Design Pattern Detection ──────────────────────────────────────────────────

def detect_design_patterns(py_files: List[Dict]) -> Dict:
    """
    Look for common patterns (good and bad) in the Python files.

    Returns:
        Dict with good_patterns (list) and anti_patterns (list).
    """
    good_patterns = []
    anti_patterns = []

    combined = "\n".join(f["content"] for f in py_files)

    # Good patterns
    if re.search(r"@dataclass", combined):
        good_patterns.append("Dataclasses used — clean data modeling.")
    if re.search(r"class.*ABC\):|from abc import", combined):
        good_patterns.append("Abstract Base Classes used — good polymorphism.")
    if re.search(r"logging\.(info|warning|error|debug|critical)", combined):
        good_patterns.append("Logging framework used (not bare print statements).")
    if re.search(r"with\s+open\(", combined):
        good_patterns.append("Context managers used for file I/O (safe resource handling).")
    if re.search(r"from typing import|: List\[|: Dict\[|: Optional\[", combined):
        good_patterns.append("Type hints used — improves readability and tooling support.")

    # Anti-patterns
    bare_excepts = len(re.findall(r"except\s*:", combined))
    if bare_excepts > 2:
        anti_patterns.append(
            f"Bare `except:` clauses found ({bare_excepts}x) — always catch specific exceptions."
        )

    print_count = len(re.findall(r"\bprint\s*\(", combined))
    if print_count > 10:
        anti_patterns.append(
            f"Heavy use of print() ({print_count}x) — consider using the logging module."
        )

    if re.search(r"global\s+\w+", combined):
        anti_patterns.append("Global variables detected — prefer passing state explicitly.")

    hardcoded_secrets = re.findall(
        r'(?:password|secret|api_key|token)\s*=\s*["\'][^"\']{4,}["\']',
        combined,
        re.IGNORECASE,
    )
    if hardcoded_secrets:
        anti_patterns.append(
            f"Possible hardcoded secrets detected ({len(hardcoded_secrets)}x). Use environment variables."
        )

    if re.search(r"import \*", combined):
        anti_patterns.append("Wildcard imports (`import *`) detected — pollutes namespace.")

    return {"good_patterns": good_patterns, "anti_patterns": anti_patterns}


# ── Performance Hints ─────────────────────────────────────────────────────────

def generate_performance_hints(py_files: List[Dict]) -> List[str]:
    """
    Suggest performance improvements based on common Python pitfalls.

    Returns:
        List of performance hint strings.
    """
    hints = []
    combined = "\n".join(f["content"] for f in py_files)

    if re.search(r"for .+ in .+:\s*\n\s+result\s*\+=", combined):
        hints.append(
            "String concatenation in a loop detected. Use ''.join(list) for better performance."
        )

    if re.search(r"\.append\(.*\)\s*\n.*\.append\(", combined):
        hints.append(
            "Multiple sequential list.append() calls — consider list comprehensions for clarity."
        )

    if not re.search(r"__slots__", combined) and re.search(r"class \w+.*:", combined):
        hints.append(
            "Consider using __slots__ in data-heavy classes to reduce memory overhead."
        )

    if re.search(r"time\.sleep\(", combined) and not re.search(r"asyncio", combined):
        hints.append(
            "time.sleep() found in a non-async context. Consider asyncio for I/O-bound concurrency."
        )

    if re.search(r"open\(.*\)\.read\(\)", combined):
        hints.append(
            "Using open().read() without context manager — use `with open(...) as f:` instead."
        )

    return hints


# ── Developer Tips ────────────────────────────────────────────────────────────

def generate_developer_tips(project_type: str, architecture: Dict) -> List[str]:
    """
    Return actionable developer tips tailored to the project type.

    Returns:
        List of tip strings.
    """
    tips = [
        "Run `black .` to auto-format your code consistently.",
        "Use `pre-commit` hooks to enforce linting before every commit.",
        "Pin your dependencies with `pip freeze > requirements.txt` for reproducibility.",
        "Write docstrings for all public functions using Google or NumPy style.",
        "Use `mypy` for static type checking to catch bugs before runtime.",
    ]

    type_tips = {
        "FastAPI / Flask API": [
            "Use Pydantic models for request/response validation in FastAPI.",
            "Add rate limiting middleware to protect your API endpoints.",
            "Document your API with OpenAPI/Swagger (FastAPI does this automatically).",
        ],
        "Machine Learning / Data Science": [
            "Version your datasets and models with DVC (Data Version Control).",
            "Use MLflow or Weights & Biases to track experiments.",
            "Always split data into train/val/test sets before any preprocessing.",
        ],
        "CLI Tool / Script": [
            "Use Click or Typer instead of argparse for cleaner CLI interfaces.",
            "Add a `--verbose` flag and use the logging module for debug output.",
            "Package your CLI tool with pyproject.toml for easy installation.",
        ],
        "Django Web App": [
            "Use Django's ORM select_related() and prefetch_related() to avoid N+1 queries.",
            "Enable Django Debug Toolbar in development for query analysis.",
            "Use environment variables for SECRET_KEY and database credentials.",
        ],
    }

    for key, extra_tips in type_tips.items():
        if key in project_type:
            tips.extend(extra_tips)
            break

    return tips[:8]  # Return top 8 tips


# ── Main Entry Point ──────────────────────────────────────────────────────────

def analyze_project(all_files: List[Dict], repo_path: str) -> Dict:
    """
    Run the full Project Understanding analysis pipeline.

    Args:
        all_files: All repository files from repo_loader.collect_all_files().
        repo_path: Root path of the repository.

    Returns:
        Comprehensive project analysis dict.
    """
    py_files = [f for f in all_files if f["extension"] == ".py"]

    project_type, type_signals = detect_project_type(all_files)
    dependencies = extract_dependencies(all_files)
    architecture = assess_architecture(all_files, repo_path)
    patterns = detect_design_patterns(py_files)
    perf_hints = generate_performance_hints(py_files)
    dev_tips = generate_developer_tips(project_type, architecture)

    # File statistics
    file_stats = {
        "total_files": len(all_files),
        "python_files": len(py_files),
        "test_files": sum(1 for f in py_files if "test" in f["relative_path"].lower()),
        "config_files": sum(1 for f in all_files if f["extension"] in {".yml", ".yaml", ".toml", ".cfg", ".ini"}),
        "doc_files": sum(1 for f in all_files if f["extension"] in {".md", ".rst", ".txt"}),
        "total_lines": sum(len(f["content"].splitlines()) for f in py_files),
    }

    # Health score (0-100)
    health = 50
    health += 10 if architecture["positives"] else 0
    health -= 5 * len(architecture["issues"])
    health += 5 * len(patterns["good_patterns"])
    health -= 5 * len(patterns["anti_patterns"])
    health += 10 if file_stats["test_files"] > 0 else 0
    health = max(0, min(100, health))

    return {
        "project_type": project_type,
        "type_signals": type_signals,
        "dependencies": dependencies,
        "architecture": architecture,
        "patterns": patterns,
        "performance_hints": perf_hints,
        "developer_tips": dev_tips,
        "file_stats": file_stats,
        "health_score": health,
    }


def build_project_summary_text(analysis: Dict) -> str:
    """
    Convert analysis dict into a text summary for LLM prompting.

    Returns:
        Formatted text summary of the project.
    """
    lines = [
        f"Project Type: {analysis['project_type']}",
        f"Architecture Style: {analysis['architecture']['style']}",
        f"Total Python Files: {analysis['file_stats']['python_files']}",
        f"Total Lines of Code: {analysis['file_stats']['total_lines']}",
        f"Test Files: {analysis['file_stats']['test_files']}",
        f"Declared Dependencies: {', '.join(analysis['dependencies']['declared'][:10]) or 'None found'}",
        "",
        "Architecture Issues: " + "; ".join(analysis["architecture"]["issues"]) if analysis["architecture"]["issues"] else "Architecture Issues: None",
        "Good Patterns: " + "; ".join(analysis["patterns"]["good_patterns"]) if analysis["patterns"]["good_patterns"] else "Good Patterns: None detected",
        "Anti-patterns: " + "; ".join(analysis["patterns"]["anti_patterns"]) if analysis["patterns"]["anti_patterns"] else "Anti-patterns: None detected",
        f"Health Score: {analysis['health_score']}/100",
    ]
    return "\n".join(lines)
