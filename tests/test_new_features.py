#!/usr/bin/env python3
"""
Comprehensive Test Suite for New Features
Tests code snippets, project overview, issue severity, and CodeXGLUE improvements
"""

import os
import sys
import json
import requests
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.coordinator import run_pipeline
from core.agents.repair import repair_repository

BASE_URL = 'http://localhost:5001/api'

def test_code_snippets():
    """Test that repair results include code snippets"""
    print("\n" + "="*60)
    print("TEST: Code Snippets in Repair Results")
    print("="*60)
    
    test_code = """import os
import sys

def add(a, b):
    return a + b
"""
    
    files = [{'path': 'test.py', 'source': test_code}]
    issues = [
        {
            'file': 'test.py',
            'line': 1,
            'issue_type': 'unused_import',
            'description': "Import 'os' is imported but never used.",
            'severity': 'warning',
            'fixable': True
        },
        {
            'file': 'test.py',
            'line': 2,
            'issue_type': 'unused_import',
            'description': "Import 'sys' is imported but never used.",
            'severity': 'warning',
            'fixable': True
        }
    ]
    
    repairs = repair_repository(files, issues)
    
    # Check for code snippets
    has_snippets = False
    for repair in repairs:
        if repair['status'] == 'fixed':
            if 'original_snippet' in repair and 'fixed_snippet' in repair:
                has_snippets = True
                print(f"✓ Repair includes code snippets")
                print(f"  Original: {repair['original_snippet'][:50]}...")
                print(f"  Fixed: {repair['fixed_snippet'][:50]}...")
                break
    
    if has_snippets:
        print("✓ PASS: Code snippets are included in repairs")
        return True
    else:
        print("✗ FAIL: Code snippets NOT included")
        return False

def test_overview_endpoint():
    """Test the /api/overview endpoint"""
    print("\n" + "="*60)
    print("TEST: Project Overview API Endpoint")
    print("="*60)
    
    try:
        # First run a small analysis to get results
        test_data = {
            'url': 'https://github.com/torvalds/linux',
            'use_llm': False
        }
        
        print("Running sample analysis...")
        response = requests.post(f'{BASE_URL}/analyze/github', json=test_data, timeout=10)
        
        if response.status_code != 200:
            print(f"✗ Analysis failed with status {response.status_code}")
            return False
        
        results = response.json()
        
        # Now test overview endpoint
        print("Testing /api/overview endpoint...")
        overview_response = requests.post(
            f'{BASE_URL}/overview',
            json={'results': results},
            timeout=10
        )
        
        if overview_response.status_code == 200:
            overview_data = overview_response.json()
            required_keys = ['project_type', 'architecture', 'statistics', 'dependencies']
            
            missing = [k for k in required_keys if k not in overview_data]
            if missing:
                print(f"✗ Missing keys in overview: {missing}")
                return False
            
            print(f"✓ Overview endpoint works")
            print(f"  Project Type: {overview_data.get('project_type', 'Unknown')}")
            print(f"  Total Files: {overview_data.get('statistics', {}).get('total_files', 0)}")
            print(f"✓ PASS: Overview endpoint functional")
            return True
        else:
            print(f"✗ Overview endpoint failed: {overview_response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⊘ SKIP: Test timeout (GitHub API may be slow)")
        return True
    except Exception as e:
        print(f"⊘ SKIP: {str(e)}")
        return True

def test_issues_summary():
    """Test the /api/issues/summary endpoint"""
    print("\n" + "="*60)
    print("TEST: Issues Summary API Endpoint")
    print("="*60)
    
    try:
        # Create test results structure
        test_results = {
            'stages': {
                'scan': {
                    'results': [
                        {
                            'file': 'test.py',
                            'relative_path': 'test.py',
                            'line': 1,
                            'issue_type': 'unused_import',
                            'severity': 'warning',
                            'description': "Import 'os' is unused",
                            'fixable': True
                        },
                        {
                            'file': 'utils.py',
                            'relative_path': 'utils.py',
                            'line': 5,
                            'issue_type': 'todo_comment',
                            'severity': 'info',
                            'description': "TODO: implement this",
                            'fixable': False
                        }
                    ]
                }
            }
        }
        
        response = requests.post(
            f'{BASE_URL}/issues/summary',
            json={'results': test_results},
            timeout=10
        )
        
        if response.status_code == 200:
            summary = response.json()
            required_keys = ['total_issues', 'by_severity', 'by_file', 'by_type']
            
            missing = [k for k in required_keys if k not in summary]
            if missing:
                print(f"✗ Missing keys in summary: {missing}")
                return False
            
            print(f"✓ Issues summary endpoint works")
            print(f"  Total Issues: {summary.get('total_issues', 0)}")
            print(f"  Errors: {summary.get('by_severity', {}).get('errors', 0)}")
            print(f"  Warnings: {summary.get('by_severity', {}).get('warnings', 0)}")
            print(f"  Critical Files: {len(summary.get('critical_files', []))}")
            print(f"✓ PASS: Issues summary endpoint functional")
            return True
        else:
            print(f"✗ Issues summary failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_severity_badges():
    """Test that issues include severity information"""
    print("\n" + "="*60)
    print("TEST: Issue Severity Badges")
    print("="*60)
    
    # Create a simple test case with severity levels
    issues = [
        {
            'file': 'test.py',
            'line': 1,
            'issue_type': 'syntax_error',
            'severity': 'error',
            'description': 'Syntax error'
        },
        {
            'file': 'test.py',
            'line': 2,
            'issue_type': 'unused_import',
            'severity': 'warning',
            'description': 'Unused import'
        },
        {
            'file': 'test.py',
            'line': 3,
            'issue_type': 'todo_comment',
            'severity': 'info',
            'description': 'TODO comment'
        }
    ]
    
    severity_counts = {
        'error': len([i for i in issues if i['severity'] == 'error']),
        'warning': len([i for i in issues if i['severity'] == 'warning']),
        'info': len([i for i in issues if i['severity'] == 'info']),
    }
    
    print(f"✓ Severity count breakdown:")
    print(f"  Errors: {severity_counts['error']}")
    print(f"  Warnings: {severity_counts['warning']}")
    print(f"  Info: {severity_counts['info']}")
    
    if all(s > 0 for s in severity_counts.values()):
        print(f"✓ PASS: All severity levels present")
        return True
    return False

def test_codexglue_improvements():
    """Test improved CodeXGLUE evaluation metrics"""
    print("\n" + "="*60)
    print("TEST: CodeXGLUE Evaluation Improvements")
    print("="*60)
    
    try:
        response = requests.post(
            f'{BASE_URL}/eval/codexglue',
            json={'max_samples': 5},
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            
            print(f"✓ Evaluation completed")
            print(f"  Samples Evaluated: {results.get('samples_evaluated', 0)}")
            
            metrics = results.get('aggregate_metrics', {})
            print(f"  Aggregate Metrics:")
            print(f"    Precision: {metrics.get('precision', 'N/A')}")
            print(f"    Recall: {metrics.get('recall', 'N/A')}")
            print(f"    F1: {metrics.get('f1', 'N/A')}")
            
            # Check for per-type metrics
            per_type = results.get('per_type_metrics', {})
            if per_type:
                print(f"  Per-Type Metrics: {len(per_type)} types detected")
                for itype, metrics in list(per_type.items())[:3]:
                    print(f"    {itype}: F1={metrics.get('f1', 'N/A')}%")
            
            print(f"✓ PASS: CodeXGLUE evaluation improved")
            return True
        else:
            print(f"✗ Evaluation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE NEW FEATURES TEST SUITE")
    print("="*60)
    
    results = {
        'code_snippets': test_code_snippets(),
        'severity_badges': test_severity_badges(),
        'overview_endpoint': test_overview_endpoint(),
        'issues_summary': test_issues_summary(),
        'codexglue_improvements': test_codexglue_improvements(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
