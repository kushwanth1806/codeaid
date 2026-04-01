#!/usr/bin/env python3
"""
Test universal_analyzer directly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.universal_analyzer import detect_unused_imports, detect_universal_issues

test_js = """const { v4: uuidv4 } = require('uuid');
const pool = require('../db');
const unused = require('unused-module');

// Create a new task
const createTask = async (req, res) => {
  try {
    const { taskName, description } = req.body;
    res.status(201).json({ task: { id: uuidv4() } });
  } catch (error) {
    console.error('Error:', error);
  }
};

module.exports = { createTask };
"""

print("=" * 80)
print("TEST: Universal Analyzer - Unused Imports in JavaScript")
print("=" * 80)

print("\n1. Testing detect_unused_imports():")
issues = detect_unused_imports("test.js", test_js, "javascript")
if issues:
    print(f"✓ Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - Line {issue['line']}: {issue['description']}")
else:
    print("✗ No issues found")

print("\n2. Testing detect_universal_issues():")
issues2 = detect_universal_issues("test.js", test_js, "javascript")
if issues2:
    print(f"✓ Found {len(issues2)} issues:")
    for issue in issues2:
        print(f"  - Line {issue['line']}: [{issue['issue_type']}] {issue['description']}")
else:
    print("✗ No issues found")

print("\n3. Testing both combined:")
all_issues = issues + issues2
if all_issues:
    print(f"✓ Found {len(all_issues)} total issues")
else:
    print("✗ No issues found")
