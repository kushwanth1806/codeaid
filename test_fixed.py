#!/usr/bin/env python3
"""
Test universal_analyzer - FIXED test data
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.universal_analyzer import detect_unused_imports, detect_universal_issues

# Test with proper code that uses pool but not unused
test_js = """const { v4: uuidv4 } = require('uuid');
const pool = require('../db');
const unused = require('unused-module');

// Create a new task
const createTask = async (req, res) => {
  try {
    const { taskName, description } = req.body;
    const result = pool.query('SELECT * FROM tasks');  // pool is used here
    res.status(201).json({ task: { id: uuidv4() } });
  } catch (error) {
    console.error('Error:', error);
  }
};

module.exports = { createTask };
"""

print("=" * 80)
print("TEST: Universal Analyzer - Fixed Test Data")
print("=" * 80)

print("\nImport Detection:")
issues = detect_unused_imports("test.js", test_js, "javascript")
if issues:
    print(f"✓ Found {len(issues)} unused imports:")
    for issue in issues:
        print(f"  - Line {issue['line']}: {issue['description']}")
        print(f"    Fixable: {issue['fixable']}")
else:
    print("✗ No unused imports found")
