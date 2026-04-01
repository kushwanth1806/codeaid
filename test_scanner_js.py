#!/usr/bin/env python3
"""
Detailed scan test for Backend-api JavaScript files
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.scanner import scan_files, _scan_single

# Test JavaScript files from Backend-api
js_files = [
    {
        "path": "src/server.js",
        "source": """const express = require('express');
const cors = require('cors');
require('dotenv').config();
const taskRoutes = require('./routes/tasks');
const unused_module = require('module');  // This is unused

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/tasks', taskRoutes);
"""
    },
    {
        "path": "src/db.js",
        "source": """const { Pool } = require('pg');
const unused_var = 42;  // This is unused

// Really really long line that exceeds the maximum character limit and should definitely trigger a line_too_long issue
const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT,
});

module.exports = pool;
"""
    }
]

print("=" * 80)
print("DETAILED SCANNER TEST")
print("=" * 80)

for file_info in js_files:
    print(f"\n📄 File: {file_info['path']}")
    print("-" * 80)
    
    issues = _scan_single(file_info['path'], file_info['source'], language='javascript')
    
    if not issues:
        print("✓ No issues found")
    else:
        print(f"✓ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - Line {issue['line']}: [{issue['issue_type']}] {issue['description']}")
            print(f"    Fixable: {issue['fixable']}, Severity: {issue['severity']}")
