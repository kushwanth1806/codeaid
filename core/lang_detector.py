"""
lang_detector.py
----------------
Language detection module for codeAID.

Detects project type and primary language(s) based on file extensions,
package manager files, and project structure.
"""

from typing import Dict, List, Set
from pathlib import Path
from collections import Counter


# Language configurations
LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "java": {".java"},
    "csharp": {".cs"},
    "go": {".go"},
    "rust": {".rs"},
    "cpp": {".cpp", ".cc", ".cxx", ".h", ".hpp"},
    "c": {".c", ".h"},
    "ruby": {".rb"},
    "php": {".php"},
    "swift": {".swift"},
    "kotlin": {".kt", ".kts"},
    "scala": {".scala"},
    "r": {".r", ".R"},
}

PROJECT_INDICATORS = {
    "python": {
        "indicators": ["setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", "poetry.lock", "Pipfile"],
        "confidence": 0.9
    },
    "javascript": {
        "indicators": ["package.json", "package-lock.json", "yarn.lock"],
        "confidence": 0.9
    },
    "typescript": {
        "indicators": ["tsconfig.json", "package.json"],
        "confidence": 0.85
    },
    "java": {
        "indicators": ["pom.xml", "build.gradle", "gradle.properties", "build.gradle.kts"],
        "confidence": 0.9
    },
    "go": {
        "indicators": ["go.mod", "go.sum", "Gopkg.toml"],
        "confidence": 0.9
    },
    "rust": {
        "indicators": ["Cargo.toml", "Cargo.lock"],
        "confidence": 0.9
    },
    "ruby": {
        "indicators": ["Gemfile", "Gemfile.lock", "Rakefile"],
        "confidence": 0.9
    },
    "csharp": {
        "indicators": [".csproj", ".sln"],
        "confidence": 0.9
    },
    "php": {
        "indicators": ["composer.json", "composer.lock"],
        "confidence": 0.85
    },
}


def detect_languages(files: List[Dict]) -> Dict:
    """
    Detect languages used in the project based on file analysis.
    
    Parameters
    ----------
    files : List[Dict]
        List of file dicts with "path" and "source" keys.
    
    Returns
    -------
    Dict with detected languages and confidence scores:
    {
        "primary_language": str,
        "detected_languages": {"lang": confidence_score, ...},
        "file_distribution": {"lang": count, ...},
        "project_type": str,
    }
    """
    file_paths = [f.get("path", "") for f in files]
    file_extensions = Counter(Path(p).suffix.lower() for p in file_paths)
    
    # Detect by extension
    language_scores = Counter()
    extension_count = Counter()
    
    for ext in file_extensions:
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if ext in exts:
                count = file_extensions[ext]
                language_scores[lang] += count
                extension_count[lang] += count
    
    # Detect by project indicators
    file_names = set(Path(p).name for p in file_paths)
    indicator_scores = Counter()
    
    for lang, config in PROJECT_INDICATORS.items():
        for indicator in config["indicators"]:
            if indicator in file_names:
                indicator_scores[lang] += 10  # High weight for project indicators
    
    # Combine scores
    total_scores = language_scores + indicator_scores
    
    if not total_scores:
        return _default_detection()
    
    # Sort by score
    sorted_langs = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    primary_lang = sorted_langs[0][0]
    primary_score = sorted_langs[0][1]
    
    # Calculate confidence (0-1)
    total = sum(total_scores.values())
    confidence = min(primary_score / total, 1.0) if total > 0 else 0.0
    
    return {
        "primary_language": primary_lang,
        "confidence": confidence,
        "detected_languages": {lang: score / total for lang, score in sorted_langs},
        "file_distribution": dict(extension_count),
        "project_indicators_found": list(file_names & _get_all_indicators()),
    }


def _default_detection() -> Dict:
    """Return default detection when no language is detected."""
    return {
        "primary_language": "unknown",
        "confidence": 0.0,
        "detected_languages": {},
        "file_distribution": {},
        "project_indicators_found": [],
    }


def _get_all_indicators() -> Set[str]:
    """Get all project indicator files across all languages."""
    indicators = set()
    for config in PROJECT_INDICATORS.values():
        indicators.update(config["indicators"])
    return indicators


def filter_files_by_language(files: List[Dict], language: str) -> List[Dict]:
    """
    Filter files to only those of a specific language.
    
    Parameters
    ----------
    files : List[Dict]
        All files
    language : str
        Language to filter for (e.g., "python", "javascript")
    
    Returns
    -------
    List[Dict] of files matching the language
    """
    if language not in LANGUAGE_EXTENSIONS:
        return files
    
    target_exts = LANGUAGE_EXTENSIONS[language]
    return [
        f for f in files
        if Path(f.get("path", "")).suffix.lower() in target_exts
    ]


def get_language_info(language: str) -> Dict:
    """
    Get detailed information about a language.
    
    Returns
    -------
    Dict with language metadata, scanner class, repair strategies, etc.
    """
    language = language.lower()
    
    language_info = {
        "python": {
            "name": "Python",
            "extensions": list(LANGUAGE_EXTENSIONS.get("python", [])),
            "package_manager": "pip",
            "build_tools": ["setuptools", "poetry", "pipenv"],
            "test_runners": ["pytest", "unittest", "nose"],
            "linters": ["pylint", "flake8", "ruff"],
            "verifier_command": "python -m py_compile",
        },
        "javascript": {
            "name": "JavaScript",
            "extensions": list(LANGUAGE_EXTENSIONS.get("javascript", [])),
            "package_manager": "npm",
            "build_tools": ["webpack", "vite", "parcel"],
            "test_runners": ["jest", "mocha", "vitest"],
            "linters": ["eslint", "jslint"],
            "verifier_command": "node --check",
        },
        "typescript": {
            "name": "TypeScript",
            "extensions": list(LANGUAGE_EXTENSIONS.get("typescript", [])),
            "package_manager": "npm",
            "build_tools": ["webpack", "tsc", "vite"],
            "test_runners": ["jest", "vitest"],
            "linters": ["eslint", "tslint"],
            "verifier_command": "tsc --noEmit",
        },
        "java": {
            "name": "Java",
            "extensions": list(LANGUAGE_EXTENSIONS.get("java", [])),
            "package_manager": "maven",
            "build_tools": ["maven", "gradle"],
            "test_runners": ["junit", "testng"],
            "linters": ["checkstyle", "pmd"],
            "verifier_command": "javac",
        },
        "go": {
            "name": "Go",
            "extensions": list(LANGUAGE_EXTENSIONS.get("go", [])),
            "package_manager": "go get",
            "build_tools": ["go build"],
            "test_runners": ["go test"],
            "linters": ["golint", "gofmt"],
            "verifier_command": "go vet",
        },
        "rust": {
            "name": "Rust",
            "extensions": list(LANGUAGE_EXTENSIONS.get("rust", [])),
            "package_manager": "cargo",
            "build_tools": ["cargo"],
            "test_runners": ["cargo test"],
            "linters": ["clippy"],
            "verifier_command": "cargo check",
        },
    }
    
    return language_info.get(language, {
        "name": language.capitalize(),
        "extensions": list(LANGUAGE_EXTENSIONS.get(language, [])),
        "package_manager": "unknown",
        "build_tools": [],
        "test_runners": [],
        "linters": [],
        "verifier_command": None,
    })
