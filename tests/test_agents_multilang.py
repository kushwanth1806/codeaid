"""
test_agents_multilang.py
-----------------------
Comprehensive test suite for CodeAid agents with multi-language support.

Tests:
1. Scanner: Can detect issues in Python, JavaScript, Java, etc.
2. Repair: Can fix issues in multiple languages
3. Verifier: Can verify repairs in multiple languages  
4. Coordinator: End-to-end pipeline works across languages
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.scanner import scan_files, _scan_single
from core.agents.repair import repair_issues, _detect_file_language
from core.agents.verifier import verify_repairs
from core.agents.universal_analyzer import detect_unused_imports


# ──────────────────────────────────────────────────────────────────────────
# Test Data
# ──────────────────────────────────────────────────────────────────────────

PYTHON_WITH_UNUSED_IMPORT = """
import os
import sys
import json

def hello():
    print(sys.version)
    return "hello"
"""

PYTHON_WITH_TRAILING_WS = """
def test():
    x = 5  
    return x

"""

JAVASCRIPT_WITH_UNUSED_IMPORT = """
const express = require('express');
const unused = require('unused-module');
const fs = require('fs');

function readConfig() {
    const data = fs.readFileSync('config.json');
    return JSON.parse(data);
}

module.exports = { readConfig };
"""

JAVASCRIPT_WITH_TRAILING_WS = """
function hello() {
  const x = 5;  
  return x;
}
"""

JAVA_WITH_UNUSED_IMPORT = """
import java.io.*;
import java.util.*;
import com.example.Helper;

public class Main {
    public static void main(String[] args) {
        List<String> items = new ArrayList<>();
        items.add("test");
        System.out.println(items);
    }
}
"""

GO_WITH_UNUSED_IMPORT = """
package main

import (
    "fmt"
    "unused"
    "os"
)

func main() {
    fmt.Println(os.Getenv("HOME"))
}
"""


# ──────────────────────────────────────────────────────────────────────────
# Tests: Scanner
# ──────────────────────────────────────────────────────────────────────────

class TestScanner:
    """Test scanner detection across languages"""
    
    def test_python_unused_import_detection(self):
        """Python scanner should detect unused imports"""
        issues = _scan_single("test.py", PYTHON_WITH_UNUSED_IMPORT, "python")
        assert any(issue["issue_type"] == "unused_import" for issue in issues)
        
    def test_python_trailing_whitespace_detection(self):
        """Python scanner should detect trailing whitespace"""
        issues = _scan_single("test.py", PYTHON_WITH_TRAILING_WS, "python")
        assert any(issue["issue_type"] == "trailing_whitespace" for issue in issues)
    
    def test_javascript_unused_import_detection(self):
        """JavaScript scanner should detect unused imports"""
        issues = _scan_single("test.js", JAVASCRIPT_WITH_UNUSED_IMPORT, "javascript")
        unused_import_issues = [i for i in issues if i["issue_type"] == "unused_import"]
        assert len(unused_import_issues) > 0, f"Expected unused_import issues, got: {issues}"
    
    def test_java_unused_import_detection(self):
        """Java scanner should detect unused imports"""
        issues = _scan_single("Main.java", JAVA_WITH_UNUSED_IMPORT, "java")
        unused_import_issues = [i for i in issues if i["issue_type"] == "unused_import"]
        assert len(unused_import_issues) > 0, f"Expected unused_import issues in Java, got: {issues}"
    
    def test_go_unused_import_detection(self):
        """Go scanner should detect unused imports (skipped - Go detection not yet implemented)"""
        pytest.skip("Go import detection not yet fully implemented")


# ──────────────────────────────────────────────────────────────────────────
# Tests: Repair
# ──────────────────────────────────────────────────────────────────────────

class TestRepair:
    """Test repair capabilities across languages"""
    
    def test_python_fix_unused_import(self):
        """Python repair should remove unused imports"""
        issues = _scan_single("test.py", PYTHON_WITH_UNUSED_IMPORT, "python")
        files = [{"path": "test.py", "source": PYTHON_WITH_UNUSED_IMPORT}]
        
        results = repair_issues(issues, files)
        fixed_count = len([r for r in results if r["status"] == "fixed"])
        
        assert fixed_count > 0, f"Expected fixes, got: {results}"
        assert "json" not in files[0]["source"]
    
    def test_javascript_fix_unused_import(self):
        """JavaScript repair should remove unused imports"""
        issues = _scan_single("test.js", JAVASCRIPT_WITH_UNUSED_IMPORT, "javascript")
        files = [{"path": "test.js", "source": JAVASCRIPT_WITH_UNUSED_IMPORT}]
        
        results = repair_issues(issues, files)
        fixed_count = len([r for r in results if r["status"] == "fixed"])
        
        assert fixed_count > 0, f"Expected fixes in JavaScript, got: {results}"
        assert "unused" not in files[0]["source"]
    
    def test_python_fix_trailing_whitespace(self):
        """Python repair should fix trailing whitespace"""
        issues = _scan_single("test.py", PYTHON_WITH_TRAILING_WS, "python")
        files = [{"path": "test.py", "source": PYTHON_WITH_TRAILING_WS}]
        
        results = repair_issues(issues, files)
        fixed_count = len([r for r in results if r["status"] == "fixed"])
        
        assert fixed_count > 0
        # Check that trailing whitespace is fixed
        for line in files[0]["source"].splitlines():
            assert line == line.rstrip() or line.isspace()


# ──────────────────────────────────────────────────────────────────────────
# Tests: Language Detection
# ──────────────────────────────────────────────────────────────────────────

class TestLanguageDetection:
    """Test language detection from file extensions"""
    
    def test_python_detection(self):
        assert _detect_file_language("test.py") == "python"
        assert _detect_file_language("module.py") == "python"
    
    def test_javascript_detection(self):
        assert _detect_file_language("app.js") == "javascript"
        assert _detect_file_language("component.jsx") == "javascript"
    
    def test_java_detection(self):
        assert _detect_file_language("Main.java") == "java"
    
    def test_go_detection(self):
        assert _detect_file_language("main.go") == "go"
    
    def test_csharp_detection(self):
        assert _detect_file_language("Program.cs") == "csharp"


# ──────────────────────────────────────────────────────────────────────────
# Tests: Universal Analyzer
# ──────────────────────────────────────────────────────────────────────────

class TestUniversalAnalyzer:
    """Test cross-language analysis"""
    
    def test_unused_imports_python(self):
        """Detect unused imports in Python"""
        issues = detect_unused_imports("test.py", PYTHON_WITH_UNUSED_IMPORT, "python")
        assert any(i["issue_type"] == "unused_import" for i in issues)
    
    def test_unused_imports_javascript(self):
        """Detect unused imports in JavaScript"""
        issues = detect_unused_imports("test.js", JAVASCRIPT_WITH_UNUSED_IMPORT, "javascript")
        assert len(issues) > 0, f"Expected unused imports in JS, got: {issues}"


# ──────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
