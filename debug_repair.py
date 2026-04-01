#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.scanner import _scan_single
from core.agents.repair import repair_issues

PYTHON_WITH_UNUSED_IMPORT = """
import os
import sys
import json

def hello():
    print(sys.version)
    return "hello"
"""

print("=" * 80)
print("DEBUG: Python Repair Test")
print("=" * 80)

print("\n1. Scanning for issues:")
issues = _scan_single("test.py", PYTHON_WITH_UNUSED_IMPORT, "python")
print(f"   Found {len(issues)} issues:")
for issue in issues:
    print(f"   - Line {issue['line']}: {issue['issue_type']} - {issue['description']}")
    print(f"     Fixable: {issue['fixable']}")

print("\n2. Attempting repairs:")
files = [{"path": "test.py", "source": PYTHON_WITH_UNUSED_IMPORT}]
results = repair_issues(issues, files)

print(f"   Repair results ({len(results)} total):")
for result in results:
    print(f"   - {result['issue_type']} @ Line {result['line']}: {result['status']}")
    print(f"     Detail: {result['detail']}")

print("\n3. Updated source code:")
print("---")
print(files[0]["source"])
print("---")
