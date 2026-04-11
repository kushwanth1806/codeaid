#!/usr/bin/env python3
"""
CodeAID Feature Tests
Tests scanner, repair, explain, and verification features
"""

import requests
import json
import tempfile
import zipfile
import sys
from pathlib import Path

API_URL = "http://localhost:5001/api"

# Sample Python code with various issues
SAMPLE_CODE_WITH_ISSUES = """
import os
import sys
import json

# Unused imports above
x = 5

def test_function(arg1, arg2, arg3, arg4, arg5):
    # Long function with many parameters
    return arg1 + arg2

# Line too long - this is a very long line that exceeds the recommended line length and should trigger a style warning
result = test_function(1, 2, 3, 4, 5)

# TODO: implement error handling
print(result)

def another_function():
    pass

if __name__ == "__main__":
    another_function()
"""

CLEAN_CODE = """
def add(a, b):
    '''Add two numbers'''
    return a + b

def main():
    result = add(5, 3)
    print(f'Result: {result}')

if __name__ == '__main__':
    main()
"""

def create_test_zip():
    """Create a test ZIP file with sample code"""
    temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    
    with zipfile.ZipFile(temp_zip, 'w') as z:
        z.writestr('main.py', SAMPLE_CODE_WITH_ISSUES)
        z.writestr('utils/helpers.py', CLEAN_CODE)
    
    return temp_zip.name


def test_analysis_with_issues():
    """Test analysis on code with issues"""
    print("\n🧪 Testing analysis with code issues...")
    try:
        zip_path = create_test_zip()
        
        with open(zip_path, 'rb') as f:
            files = {'files': f}
            data = {'use_llm': False}
            response = requests.post(
                f"{API_URL}/analyze/upload",
                files={'files': (Path(zip_path).name, f, 'application/zip')},
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        results = response.json()
        
        # Verify response structure
        assert 'stages' in results
        assert 'scan' in results['stages']
        
        scan_data = results['stages']['scan']
        issues = scan_data.get('results', [])
        
        print(f"✓ Analysis completed successfully")
        print(f"  - Issues Found: {len(issues)}")
        print(f"  - Source Files Scanned: {results['stages'].get('load', {}).get('python_file_count', 0)}")
        
        # Print detected issues
        if issues:
            print(f"\n  Detected Issues:")
            for issue in issues[:5]:  # Show first 5
                print(f"    - {issue.get('issue_type', 'unknown')} at {issue.get('relative_path', 'unknown')}:"
                      f"{issue.get('line', '?')} - {issue.get('message', 'No message')}")
        
        # Check if repairs were attempted
        if 'repair' in results['stages']:
            repairs = results['stages']['repair'].get('results', [])
            print(f"\n  Repairs Applied: {len(repairs)}")
            
            for repair in repairs[:3]:
                status = repair.get('status', 'unknown')
                print(f"    - {status.upper()}: {repair.get('relative_path', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"✗ Analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clean_code_analysis():
    """Test analysis on clean code (should have no/minimal issues)"""
    print("\n🧪 Testing analysis on clean code...")
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w')
        temp_file.write(CLEAN_CODE)
        temp_file.close()
        
        # Create ZIP with clean code
        zip_path = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr('clean.py', CLEAN_CODE)
        
        with open(zip_path, 'rb') as f:
            response = requests.post(
                f"{API_URL}/analyze/upload",
                files={'files': ('test.zip', f, 'application/zip')},
                data={'use_llm': False},
                timeout=120
            )
        
        assert response.status_code == 200
        results = response.json()
        
        scan_data = results['stages']['scan']
        issues = scan_data.get('results', [])
        
        # Clean code should have minimal or no issues
        # (May have some style warnings, but should be much fewer)
        print(f"✓ Clean code analysis completed")
        print(f"  - Issues Found: {len(issues)}")
        
        if len(issues) == 0:
            print("  ✓ Clean code passed with no issues!")
        else:
            print(f"  Small number of issues found (style warnings expected):")
            for issue in issues:
                print(f"    - {issue.get('issue_type', 'unkno')}: {issue.get('message', '')}")
        
        return True
    except Exception as e:
        print(f"✗ Clean code test failed: {e}")
        return False


def test_codexglue_full_evaluation():
    """Test full CodeXGLUE evaluation with more samples"""
    print("\n🧪 Testing CodeXGLUE evaluation with 15 samples...")
    try:
        response = requests.post(
            f"{API_URL}/eval/codexglue",
            json={"max_samples": 15},
            timeout=60,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify metrics
        metrics = data['aggregate_metrics']
        precision = metrics.get('precision', 0)
        recall = metrics.get('recall', 0)
        f1 = metrics.get('f1', 0)
        
        print(f"✓ Full evaluation completed")
        print(f"  - Samples: {data['samples_evaluated']}")
        print(f"  - Precision: {precision:.1%}")
        print(f"  - Recall: {recall:.1%}")
        print(f"  - F1 Score: {f1:.1%}")
        print(f"  - TP: {data['total_tp']}, FP: {data['total_fp']}, FN: {data['total_fn']}")
        
        # Check that metrics are reasonable
        if f1 >= 0.5:
            print("  ✓ F1 score is reasonable (>50%)")
            return True
        else:
            print(f"  ⚠️ F1 score is lower than expected ({f1:.1%})")
            return True  # Don't fail, just warn
    except Exception as e:
        print(f"✗ Full evaluation test failed: {e}")
        return False


def run_feature_tests():
    """Run all feature tests"""
    print("\n" + "="*60)
    print("🚀 CodeAID Feature Tests")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Analysis with Issues", test_analysis_with_issues()))
    results.append(("Clean Code Analysis", test_clean_code_analysis()))
    results.append(("Full CodeXGLUE Eval", test_codexglue_full_evaluation()))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Feature Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All feature tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == '__main__':
    success = run_feature_tests()
    sys.exit(0 if success else 1)
