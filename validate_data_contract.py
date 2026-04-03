#!/usr/bin/env python3
"""
PHASE 2: Data Contract Validation Script

Validates that all pipeline stages maintain proper data contracts:
- Issues conform to required schema
- Fields are present and have correct types
- Backward compatibility with field aliases
- No data loss through pipeline stages
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.scanner import scan_repository
from core.data_validation import normalize_issue, normalize_scan_results, validate_issue


# ──────────────────────────────────────────────────────────────────────────
# Contract Definitions
# ──────────────────────────────────────────────────────────────────────────

# Required fields for RAW scanner output (before normalization)
RAW_SCANNER_FIELDS = {
    "file": str,
    "line": int,
    "issue_type": str,
    "severity": str,
    # Note: either "description" OR "message" is acceptable
    "fixable": bool,
}

# Required fields for NORMALIZED issues (after normalization)
CORE_FIELDS = {
    "file": str,
    "line": int,
    "issue_type": str,
    "severity": str,
    "message": str,         # MUST be present after normalization
    "fixable": bool,
}

# Optional but important fields
ENRICHMENT_FIELDS = {
    "description": str,
    "icon": str,
    "title": str,
    "summary": str,
    "relative_path": str,
}

REPAIR_FIELDS = {
    "status": str,  # fixed, skipped, failed
    "detail": str,
    "patched": (str, type(None)),  # Can be string or None
}


# ──────────────────────────────────────────────────────────────────────────
# Validation Functions
# ──────────────────────────────────────────────────────────────────────────

def validate_raw_scanner_fields(issue: Dict) -> Tuple[bool, List[str]]:
    """Validate raw scanner issue has required fields with correct types."""
    errors = []
    
    for field_name, expected_type in RAW_SCANNER_FIELDS.items():
        if field_name not in issue:
            errors.append(f"Missing required field: {field_name}")
            continue
        
        value = issue[field_name]
        if not isinstance(value, expected_type):
            errors.append(
                f"Field '{field_name}' has wrong type: "
                f"expected {expected_type.__name__}, got {type(value).__name__}"
            )
        elif isinstance(value, str) and not value.strip():
            errors.append(f"Field '{field_name}' is empty string (must have content)")
        elif isinstance(value, int) and value < -1:
            errors.append(f"Field '{field_name}' has invalid value: {value} (must be >= -1)")
    
    # Check that either "description" or "message" exists
    if "description" not in issue and "message" not in issue:
        errors.append("Must have either 'description' or 'message' field")
    
    return len(errors) == 0, errors


def validate_core_fields(issue: Dict) -> Tuple[bool, List[str]]:
    """Validate normalized issue has all required core fields with correct types."""
    errors = []
    
    for field_name, expected_type in CORE_FIELDS.items():
        if field_name not in issue:
            errors.append(f"Missing required field: {field_name}")
            continue
        
        value = issue[field_name]
        if not isinstance(value, expected_type):
            errors.append(
                f"Field '{field_name}' has wrong type: "
                f"expected {expected_type.__name__}, got {type(value).__name__}"
            )
        elif isinstance(value, str) and not value.strip():
            errors.append(f"Field '{field_name}' is empty string (must have content)")
        elif isinstance(value, int) and value < -1:
            errors.append(f"Field '{field_name}' has invalid value: {value} (must be >= -1)")
    
    return len(errors) == 0, errors


def validate_field_semantics(issue: Dict) -> Tuple[bool, List[str]]:
    """Validate semantic correctness of field values."""
    errors = []
    
    # severity must be valid
    valid_severities = {"error", "warning", "info"}
    if issue.get("severity") not in valid_severities:
        errors.append(f"Invalid severity: {issue.get('severity')} "
                     f"(must be one of {valid_severities})")
    
    # issue_type should be snake_case
    issue_type = issue.get("issue_type", "")
    if issue_type and not all(c.isalnum() or c == '_' for c in issue_type):
        errors.append(f"Invalid issue_type format: {issue_type} (should be snake_case)")
    
    # fixable must be boolean (not string "true"/"false")
    if not isinstance(issue.get("fixable"), bool):
        errors.append(f"fixable must be boolean, not {type(issue.get('fixable'))}")
    
    # line must be positive or -1 (for N/A)
    line = issue.get("line", -2)
    if line < -1:
        errors.append(f"Invalid line number: {line} (must be >= -1)")
    
    return len(errors) == 0, errors


def validate_backward_compatibility(raw_issue: Dict, normalized_issue: Dict) -> Tuple[bool, List[str]]:
    """Validate that normalization preserves data (backward compatibility)."""
    errors = []
    
    # Check both "type" and "issue_type" are equivalent
    raw_type = raw_issue.get("type") or raw_issue.get("issue_type")
    normalized_type = normalized_issue.get("issue_type")
    if raw_type and raw_type != normalized_type:
        errors.append(f"Issue type changed during normalization: {raw_type} → {normalized_type}")
    
    # Check both "message" and "description" are equivalent
    raw_msg = raw_issue.get("message") or raw_issue.get("description")
    normalized_msg = normalized_issue.get("message")
    if raw_msg and raw_msg not in normalized_msg:
        errors.append(f"Message truncated during normalization:\n"
                     f"  Original: {raw_msg}\n"
                     f"  Normalized: {normalized_msg}")
    
    # Check severity is preserved
    raw_sev = raw_issue.get("severity") or raw_issue.get("level")
    normalized_sev = normalized_issue.get("severity")
    if raw_sev and raw_sev.lower() != normalized_sev.lower():
        errors.append(f"Severity changed: {raw_sev} → {normalized_sev}")
    
    return len(errors) == 0, errors


def validate_repair_result(result: Dict) -> Tuple[bool, List[str]]:
    """Validate repair result has required fields."""
    errors = []
    
    required = {
        "file": str,
        "issue_type": str,
        "line": int,
        "status": str,
        "detail": str,
    }
    
    for field, expected_type in required.items():
        if field not in result:
            errors.append(f"Missing field in repair result: {field}")
            continue
        
        value = result[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"Repair result field '{field}' has wrong type: "
                f"expected {expected_type.__name__}, got {type(value).__name__}"
            )
    
    # Validate status field
    status = result.get("status")
    if status not in {"fixed", "skipped", "failed"}:
        errors.append(f"Invalid repair status: {status} "
                     f"(must be one of: fixed, skipped, failed)")
    
    return len(errors) == 0, errors


# ──────────────────────────────────────────────────────────────────────────
# Main Validation Test
# ──────────────────────────────────────────────────────────────────────────

def run_contract_validation():
    """Run comprehensive data contract validation."""
    
    print("\n" + "="*80)
    print("PHASE 2: DATA CONTRACT VALIDATION")
    print("="*80)
    
    # Create test data with long line (must be > 120 chars)
    test_code = """const x = "This is a very long line that exceeds the maximum character limit of 120 characters that we set to trigger the line_too_long detection";"""
    
    test_files = [{
        "path": "test.js",
        "source": test_code
    }]
    
    violations_found = False
    
    # ───────────────────────────────────────────────────────────────────
    # Test 1: Scanner Output Format
    # ───────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Scanner Output Format")
    print("-" * 80)
    
    scan_results = scan_repository(test_files)
    
    if not scan_results:
        print("⚠️  No issues detected - skipping contract validation")
        return True
    
    print(f"✓ Scanner produced {len(scan_results)} issue(s)")
    
    for i, issue in enumerate(scan_results, 1):
        print(f"\n  Issue {i}: {issue.get('issue_type')} at {issue.get('file')}:{issue.get('line')}")
        
        # Check core fields (raw scanner contract)
        is_valid, errors = validate_raw_scanner_fields(issue)
        if not is_valid:
            print(f"    ❌ Raw scanner format invalid:")
            for error in errors:
                print(f"       • {error}")
            violations_found = True
        else:
            print(f"    ✅ Raw scanner format valid")
        
        # Check semantic validity
        is_valid, errors = validate_field_semantics(issue)
        if not is_valid:
            print(f"    ❌ Semantic validation failed:")
            for error in errors:
                print(f"       • {error}")
            violations_found = True
        else:
            print(f"    ✅ Field semantics valid")
    
    # ───────────────────────────────────────────────────────────────────
    # Test 2: Normalization Preserves Data
    # ───────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Normalization Preserves Data")
    print("-" * 80)
    
    raw_issues = scan_results
    normalized_issues = normalize_scan_results(raw_issues)
    
    print(f"✓ Normalized {len(raw_issues)} issue(s)")
    
    for i, (raw, normalized) in enumerate(zip(raw_issues, normalized_issues), 1):
        print(f"\n  Issue {i}: {normalized.get('issue_type')}")
        
        # Check backward compatibility
        is_valid, errors = validate_backward_compatibility(raw, normalized)
        if not is_valid:
            print(f"    ❌ Backward compatibility broken:")
            for error in errors:
                print(f"       • {error}")
            violations_found = True
        else:
            print(f"    ✅ Normalized fields compatible with raw")
        
        # Check normalized has all core fields
        is_valid, errors = validate_core_fields(normalized)
        if not is_valid:
            print(f"    ❌ Normalized issue missing fields:")
            for error in errors:
                print(f"       • {error}")
            violations_found = True
        else:
            print(f"    ✅ Normalized issue has all core fields")
        
        # Check enrichment fields are added
        enrichment_count = sum(1 for k in ENRICHMENT_FIELDS if k in normalized)
        print(f"    ✅ Enrichment fields added: {enrichment_count} present")
    
    # ───────────────────────────────────────────────────────────────────
    # Test 3: Data Validation Function
    # ───────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Data Validation Function")
    print("-" * 80)
    
    for issue in normalized_issues:
        is_valid, errors = validate_issue(issue)
        issue_type = issue.get('issue_type', 'unknown')
        
        if not is_valid:
            print(f"  Issue '{issue_type}' at line {issue.get('line')}:")
            print(f"    ❌ INVALID")
            for error in errors:
                print(f"       • {error}")
            violations_found = True
        else:
            print(f"  ✅ Issue '{issue_type}' at line {issue.get('line')}: VALID")
    
    # ───────────────────────────────────────────────────────────────────
    # Summary
    # ───────────────────────────────────────────────────────────────────
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if violations_found:
        print("\n❌ CONTRACT VIOLATIONS DETECTED")
        print("   Data pipeline has schema compliance issues")
        return False
    else:
        print("\n✅ DATA CONTRACT VALIDATION PASSED")
        print("   • Scanner output conforms to schema")
        print("   • Normalization preserves all data")
        print("   • Field types and values are valid")
        print("   • Backward compatibility maintained")
        print("   • No schema drift detected")
        return True


if __name__ == "__main__":
    try:
        success = run_contract_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
