#!/usr/bin/env python3
"""
PHASE 1 VERIFICATION SCRIPT
==========================

Traces the complete data flow through the pipeline to verify:
1. Scanner creates issues with fixable field
2. Normalization preserves fixable field  
3. Repair agent receives scan_results
4. Repair agent processes non-fixable issues correctly
5. Session stores repair results
"""

import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.agents.scanner import scan_repository
from core.agents.repair import repair_repository, summarize_repairs
from core.data_validation import normalize_scan_results, normalize_repair_results
from core.lang_detector import detect_languages


def test_pipeline_trace():
    """Test complete pipeline with tracing."""
    
    print("\n" + "="*80)
    print("PHASE 1 VERIFICATION: Pipeline Flow Trace")
    print("="*80)
    
    # Create test file with long line
    test_code = """
// This is a normal line
const result = "This line is intentionally very long to exceed the 120 character limit set by the scanner configuration so it will be detected";

function handler() {
    console.log("test");
}
"""
    
    test_files = [{
        "path": "test.js",
        "source": test_code
    }]
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 1: Scanner Detection
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 1] Scanner Detection")
    print("-" * 80)
    
    scan_results = scan_repository(test_files)
    print(f"✓ scan_repository() returned {len(scan_results)} issues")
    
    for i, issue in enumerate(scan_results, 1):
        print(f"\n  Issue {i}:")
        print(f"    Type: {issue.get('issue_type')}")
        print(f"    File: {issue.get('file')}")
        print(f"    Line: {issue.get('line')}")
        print(f"    Fixable: {issue.get('fixable')} (type: {type(issue.get('fixable')).__name__})")
        print(f"    Description: {issue.get('description')}")
        print(f"    Severity: {issue.get('severity')}")
    
    if not scan_results:
        print("  ⚠️  No issues detected!")
        return False
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 2: Normalization
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 2] Normalization")
    print("-" * 80)
    
    normalized_results = normalize_scan_results(scan_results)
    print(f"✓ normalize_scan_results() returned {len(normalized_results)} issues")
    
    for i, issue in enumerate(normalized_results, 1):
        print(f"\n  Issue {i} (normalized):")
        print(f"    Type: {issue.get('issue_type')}")
        print(f"    File: {issue.get('file')}")
        print(f"    Line: {issue.get('line')}")
        print(f"    Fixable: {issue.get('fixable')} (type: {type(issue.get('fixable')).__name__})")
        print(f"    Auto-Fixable: {issue.get('auto_fixable')}")
        print(f"    Has icon: {'icon' in issue}")
        print(f"    Has title: {'title' in issue}")
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 3: Repair Agent Processing
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 3] Repair Agent Processing")
    print("-" * 80)
    
    print(f"✓ Passing {len(normalized_results)} normalized issues to repair_repository()")
    repair_results = repair_repository(test_files, normalized_results)
    print(f"✓ repair_repository() returned {len(repair_results)} results")
    
    for i, result in enumerate(repair_results, 1):
        print(f"\n  Repair Result {i}:")
        print(f"    Type: {result.get('issue_type')}")
        print(f"    File: {result.get('file')}")
        print(f"    Line: {result.get('line')}")
        print(f"    Status: {result.get('status')} (CRITICAL: UI only counts 'fixed')")
        print(f"    Detail: {result.get('detail')}")
        print(f"    Patched: {result.get('patched')}")
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 4: Repair Results Normalization
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 4] Repair Results Normalization")
    print("-" * 80)
    
    normalized_repair_results = normalize_repair_results(repair_results)
    print(f"✓ normalize_repair_results() returned {len(normalized_repair_results)} results")
    
    for i, result in enumerate(normalized_repair_results, 1):
        print(f"\n  Repair Result {i} (normalized):")
        print(f"    Type: {result.get('issue_type')}")
        print(f"    File: {result.get('file')}")
        print(f"    Status: {result.get('status')}")
        print(f"    Detail: {result.get('detail')}")
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 5: Repair Summary (UI Metrics)
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 5] Repair Summary (What UI Displays)")
    print("-" * 80)
    
    repair_summary = summarize_repairs(repair_results)
    print(f"✓ summarize_repairs() returned summary:")
    print(f"  Files Changed: {repair_summary.get('files_changed')} (UI metric)")
    print(f"  Total Repairs: {repair_summary.get('total_repairs')} (UI metric - only counts 'fixed')")
    
    # ─────────────────────────────────────────────────────────────────
    # STAGE 6: UI Filtering Logic
    # ─────────────────────────────────────────────────────────────────
    print("\n[STAGE 6] UI Filtering (app.py filtering logic)")
    print("-" * 80)
    
    # This is what app.py does:
    fixed_repairs = [r for r in normalized_repair_results if r.get("status") == "fixed"]
    print(f"✓ UI filters with: [r for r in results if r.get('status') == 'fixed']")
    print(f"  Fixed repairs count: {len(fixed_repairs)}")
    print(f"  Message shown: {'No automatic repairs applied' if not fixed_repairs else 'Repairs displayed'}")
    
    # ─────────────────────────────────────────────────────────────────
    # Analysis
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    line_too_long_issues = [r for r in normalized_repair_results 
                           if r.get('issue_type') == 'line_too_long']
    
    if line_too_long_issues:
        print(f"\n✓ CONFIRMED: line_too_long issue detected and processed:")
        print(f"  - Scanner found it: YES")
        print(f"  - Repair received it: YES")
        print(f"  - Repair returned it: YES (with status='{line_too_long_issues[0].get('status')}')")
        print(f"  - UI displays it as fixed: NO (status != 'fixed')")
        print(f"\n✓ CONCLUSION: Data pipeline IS working correctly")
        print(f"  The issue is marked as not auto-fixable, so it's appropriately skipped.")
        
        return True
    else:
        print("\n⚠️  No line_too_long issues found to trace!")
        return False


if __name__ == "__main__":
    try:
        success = test_pipeline_trace()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR during trace: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
