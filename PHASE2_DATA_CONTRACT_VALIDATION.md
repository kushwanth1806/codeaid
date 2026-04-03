# PHASE 2: DATA CONTRACT VALIDATION
## Validates the data contract between pipeline agents

**Required Issue Contract:**
```
{
  # Core Fields (Required)
  "file": str,              # File path
  "line": int,              # Line number (1-based)
  "issue_type": str,        # Type of issue: unused_import, line_too_long, etc.
  "severity": str,          # Level: error, warning, info
  "message": str,           # Human-readable description
  "fixable": bool,          # Can auto-repair fix this?
  
  # Optional Enrichment Fields
  "description": str,       # Alias for message
  "status": str,            # (In repair results): fixed, skipped, failed
  "detail": str,            # (In repair results): Why it was fixed/skipped
}
```

**Validation Rules:**
1. All core fields must be present in normalized issues
2. Field types must be correct (str, int, bool)
3. Backup fields (description→message) must be equivalent
4. `fixable` field must exist and be boolean
5. No unknown fields that indicate schema drift

## Validator Output

### Issue Format Compliance: ✅ PASS
- Scanner creates issues with correct format
- Normalization preserves all required fields
- No schema drift detected

### Field Validation: ✅ PASS
- All issues have required fields
- All field types are correct
- Fixable field is always boolean

### Backward Compatibility: ✅ PASS
- normalize_issue() handles both "type" and "issue_type"
- normalize_issue() handles both "message" and "description"  
- No breaking changes in field names

### Data Quality: ✅ PASS
- No null/undefined in required fields
- All string fields are non-empty
- All numeric fields are positive (except -1 for "N/A")

## Conclusion: Data Contract Valid ✅
All pipeline stages maintain proper data contracts.
No contract violations detected.
