#!/usr/bin/env python3
"""
Debug universal_analyzer
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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

lines = test_js.splitlines()

print("=" * 80)
print("DEBUG: JavaScript Import Detection")
print("=" * 80)

# Manual parsing
imports_info = []

# const x = require(...)
for lineno, line in enumerate(lines, start=1):
    match = re.match(r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(", line)
    if match:
        import_name = match.group(1)
        imports_info.append((import_name, lineno, line))
        print(f"\n✓ Found import on line {lineno}: {import_name}")
        print(f"  Raw: {line}")

print(f"\nTotal imports found: {len(imports_info)}")

# Now check if they are used
source_without_imports = re.sub(r"^\s*(?:import|const\s+\w+\s*=\s*require)\s+.+$", "", test_js, flags=re.MULTILINE)

print("\n" + "=" * 80)
print("Checking usage of imports:")
print("=" * 80)

for name, lineno, original_line in imports_info:
    pattern = rf'\b{re.escape(name)}\b'
    if re.search(pattern, source_without_imports):
        print(f"✓ '{name}' is USED somewhere in the code")
    else:
        print(f"✗ '{name}' is NOT USED - should be flagged as unused!")
        print(f"  Searching for: {pattern}")
