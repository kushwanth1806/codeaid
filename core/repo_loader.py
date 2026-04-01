"""
repo_loader.py
--------------
Handles loading Python source files from a GitHub URL (via git clone)
or from an uploaded ZIP archive.  Returns a flat list of dicts:
  { "path": relative_path_str, "source": source_code_str }
"""

import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_repository(source: str, is_zip: bool = False) -> Dict:
    """
    Multi-language repository loader: Load from ZIP or GitHub URL.
    
    Returns a dict with:
      {
        "repo_path": str,
        "python_files": List[Dict],  # Python files only (backward compat)
        "all_source_files": List[Dict],  # All source code files
        "all_files": List[Dict],  # Config, docs, and source
        "temp_dir": str
      }
    """
    temp_dir = None
    try:
        if is_zip:
            with open(source, 'rb') as f:
                zip_bytes = f.read()
            temp_dir, py_files = load_from_zip(zip_bytes)
        else:
            temp_dir, py_files = load_from_github(source)
        
        # Collect all files
        all_files = _collect_all_files(temp_dir)
        all_source_files = _collect_source_files(temp_dir)  # NEW: all source code
        repo_path = temp_dir
        
        return {
            "repo_path": repo_path,
            "python_files": py_files,  # For backward compatibility
            "all_source_files": all_source_files,  # New: multi-language
            "all_files": all_files,
            "temp_dir": temp_dir,
        }
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def cleanup_repo(temp_dir: str) -> None:
    """Clean up temporary repository directory."""
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def load_from_github(url: str) -> tuple:
    """
    Clone *url* into a temporary directory and collect every .py file.

    Parameters
    ----------
    url : str
        Public GitHub repository URL (https or git).

    Returns
    -------
    tuple (temp_dir, List[Dict])  –  (directory_path, [{"path": str, "source": str}, ...])
    """
    import git  # gitpython

    tmp = tempfile.mkdtemp(prefix="codeaid_gh_")
    try:
        git.Repo.clone_from(url, tmp, depth=1)
        python_files = _collect_python_files(tmp)
        return tmp, python_files
    except Exception as exc:
        # Clean up on error
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository: {exc}") from exc


def load_from_zip(zip_bytes: bytes) -> tuple:
    """
    Extract *zip_bytes* into a temporary directory and collect every .py file.

    Parameters
    ----------
    zip_bytes : bytes
        Raw content of the uploaded ZIP file.

    Returns
    -------
    tuple (temp_dir, List[Dict])  –  (directory_path, [{"path": str, "source": str}, ...])
    """
    tmp = tempfile.mkdtemp(prefix="codeaid_zip_")
    zip_path = os.path.join(tmp, "upload.zip")
    try:
        with open(zip_path, "wb") as fh:
            fh.write(zip_bytes)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        python_files = _collect_python_files(tmp)
        return tmp, python_files
    except zipfile.BadZipFile as exc:
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("Uploaded file is not a valid ZIP archive.") from exc
    except Exception as exc:
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"Failed to load ZIP: {exc}") from exc


def get_repo_structure(files: List[Dict]) -> Dict:
    """
    Build a lightweight structural summary of the repository.

    Returns a dict with:
      - file_count       : int
      - total_lines      : int
      - directories      : set of unique parent directories
      - file_paths       : list of relative paths
    """
    directories = set()
    total_lines = 0
    for f in files:
        p = Path(f["path"])
        if p.parent != Path("."):
            directories.add(str(p.parent))
        total_lines += f["source"].count("\n") + 1

    return {
        "file_count": len(files),
        "total_lines": total_lines,
        "directories": directories,
        "file_paths": [f["path"] for f in files],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enrich_file_dict(file_dict: Dict) -> Dict:
    """
    Enrich a basic file dict with additional fields needed by various agents.
    
    Input:  {"path": str, "source": str}
    Output: {
        "path": str,
        "source": str,
        "relative_path": str,  (same as "path")
        "content": str,         (same as "source")
        "name": str,            (filename without directory)
        "extension": str,       (.py, .txt, etc.)
    }
    """
    from pathlib import Path as PathlibPath
    
    rel_path = file_dict.get("path", "")
    source = file_dict.get("source", "")
    
    p = PathlibPath(rel_path)
    name = p.name
    ext = p.suffix  # includes the dot (e.g., ".py")
    
    enriched = {
        "path": rel_path,
        "source": source,
        "relative_path": rel_path,
        "content": source,
        "name": name,
        "extension": ext,
    }
    return enriched


def _collect_all_files(root: str) -> List[Dict]:
    """Walk *root* and return enriched dicts for config, docs, and Python files."""
    collected: List[Dict] = []
    root_path = Path(root)

    # Directories we always skip
    skip_dirs = {
        ".git", "__pycache__", ".tox", "node_modules",
        "venv", ".venv", "env", "dist", "build", ".eggs",
        "upload.zip",  # Skip the upload.zip file from ZIP extractions
    }

    # File patterns to collect
    interesting_extensions = {".py", ".txt", ".md", ".rst", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".json"}
    interesting_names = {
        "setup.py", "setup.cfg", "requirements.txt", "requirements-dev.txt",
        "pyproject.toml", "Dockerfile", ".env.example", "pytest.ini",
        "tox.ini", ".github", "Makefile", "README", "readme.md", "readme.rst",
    }

    for file_path in root_path.rglob("*"):
        # Skip hidden and virtual-env directories
        if any(part in skip_dirs for part in file_path.parts):
            continue
        
        # Skip directories (we only want files)
        if file_path.is_dir():
            continue
        
        # Check if this file is interesting
        is_interesting = (
            file_path.suffix in interesting_extensions or
            file_path.name in interesting_names or
            file_path.name.lower().startswith("readme") or
            file_path.name.lower().startswith("dockerfile")
        )
        
        if not is_interesting:
            continue
        
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            rel_path = str(file_path.relative_to(root_path))
            file_dict = {"path": rel_path, "source": source}
            enriched = _enrich_file_dict(file_dict)
            collected.append(enriched)
        except (OSError, UnicodeDecodeError):
            continue  # Skip unreadable files

    return collected


def _collect_python_files(root: str) -> List[Dict]:
    """Walk *root* and return source dicts for every .py file found."""
    collected: List[Dict] = []
    root_path = Path(root)

    # Directories we always skip
    skip_dirs = {
        ".git", "__pycache__", ".tox", "node_modules",
        "venv", ".venv", "env", "dist", "build", ".eggs",
    }

    for py_file in root_path.rglob("*.py"):
        # Skip hidden / virtual-env directories
        if any(part in skip_dirs for part in py_file.parts):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            rel_path = str(py_file.relative_to(root_path))
            file_dict = {"path": rel_path, "source": source}
            enriched = _enrich_file_dict(file_dict)
            collected.append(enriched)
        except OSError:
            continue  # unreadable file – skip silently

    return collected


def _collect_source_files(root: str) -> List[Dict]:
    """
    Walk *root* and return source code files for ALL supported languages.
    
    Supports: Python, JavaScript, TypeScript, Java, C#, Go, Rust, Ruby, PHP, etc.
    """
    collected: List[Dict] = []
    root_path = Path(root)

    skip_dirs = {
        ".git", "__pycache__", ".tox", "node_modules",
        ".venv", "venv", "env", "dist", "build", ".eggs",
        "target", "bin", "obj",  # Java, C#
    }

    # Supported source code extensions
    source_extensions = {
        # Python
        ".py",
        # JavaScript/TypeScript
        ".js", ".jsx", ".mjs", ".ts", ".tsx",
        # Java
        ".java",
        # C#
        ".cs",
        # C/C++
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
        # Go
        ".go",
        # Rust
        ".rs",
        # Ruby
        ".rb",
        # PHP
        ".php", ".phtml",
        # Swift
        ".swift",
        # Kotlin
        ".kt", ".kts",
        # Scala
        ".scala",
        # R
        ".r", ".R",
        # Shell
        ".sh", ".bash",
        # SQL
        ".sql",
    }

    for file_path in root_path.rglob("*"):
        # Skip hidden and build directories
        if any(part in skip_dirs for part in file_path.parts):
            continue
        
        if file_path.is_dir():
            continue
        
        # Check if source file
        if file_path.suffix.lower() not in source_extensions:
            continue
        
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            rel_path = str(file_path.relative_to(root_path))
            file_dict = {"path": rel_path, "source": source}
            enriched = _enrich_file_dict(file_dict)
            collected.append(enriched)
        except (OSError, UnicodeDecodeError):
            continue

    return collected
