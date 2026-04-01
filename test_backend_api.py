#!/usr/bin/env python3
"""
Test script to debug CodeAid's multi-language support on Backend-api repo
"""

import sys
from pathlib import Path

# Add the codeaid package to path
sys.path.insert(0, str(Path(__file__).parent))

from core.repo_loader import load_repository
from core.agents.coordinator import run_pipeline

def test_loading():
    """Test loading the Backend-api repository"""
    print("=" * 80)
    print("TEST 1: Loading Backend-api Repository from GitHub")
    print("=" * 80)
    
    try:
        repo_data = load_repository("https://github.com/kushwanth1806/Backend-api", is_zip=False)
        
        print(f"\n✓ Repository loaded successfully")
        print(f"  - Repo path: {repo_data['repo_path']}")
        print(f"  - Python files DETECTED: {len(repo_data['python_files'])}")
        print(f"    {[f['path'] for f in repo_data['python_files'][:5]]}")
        
        print(f"\n  - ALL SOURCE FILES DETECTED: {len(repo_data['all_source_files'])}")
        for f in repo_data['all_source_files']:
            print(f"    - {f['path']}")
        
        print(f"\n  - ALL FILES (configs, docs, etc): {len(repo_data['all_files'])}")
        for f in repo_data['all_files'][:10]:
            print(f"    - {f['path']}")
        
        return repo_data
        
    except Exception as e:
        print(f"✗ FAILED TO LOAD: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_scanning(repo_data):
    """Test scanning files"""
    print("\n" + "=" * 80)
    print("TEST 2: Scanning Files for Issues")
    print("=" * 80)
    
    from core.agents.scanner import scan_repository
    
    try:
        # Test with all_source_files
        print(f"\nScanning {len(repo_data['all_source_files'])} source files...")
        issues = scan_repository(repo_data['all_source_files'])
        
        print(f"\n✓ Scan complete")
        print(f"  - Total issues found: {len(issues)}")
        
        # Group by file
        by_file = {}
        for issue in issues:
            file_path = issue.get('file', 'unknown')
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(issue)
        
        print(f"  - Issues by file:")
        for file_path, file_issues in sorted(by_file.items()):
            print(f"    - {file_path}: {len(file_issues)} issues")
            for issue in file_issues[:3]:
                print(f"      * {issue['issue_type']} @ Line {issue['line']}: {issue['description']}")
        
        return issues
        
    except Exception as e:
        print(f"✗ SCANNING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_full_pipeline(source):
    """Test full pipeline"""
    print("\n" + "=" * 80)
    print("TEST 3: Full Pipeline Analysis")
    print("=" * 80)
    
    try:
        print(f"\nAnalyzing repository: {source}")
        results = run_pipeline(source, is_zip=False, use_llm=False)
        
        print(f"\n✓ Pipeline complete!")
        
        # Print results
        load_results = results['stages'].get('load', {})
        print(f"\n  Stage 1 - Load:")
        print(f"    - Python files: {load_results.get('python_file_count', 0)}")
        print(f"    - Total files: {load_results.get('total_file_count', 0)}")
        
        scan_results = results['stages'].get('scan', {}).get('summary', {})
        print(f"\n  Stage 2 - Scan:")
        print(f"    - Total issues: {scan_results.get('total_issues', 0)}")
        print(f"    - By severity: {scan_results.get('by_severity', {})}")
        print(f"    - By type: {scan_results.get('by_type', {})}")
        
        repair_results = results['stages'].get('repair', {}).get('summary', {})
        print(f"\n  Stage 3 - Repair:")
        print(f"    - Files changed: {repair_results.get('files_changed', 0)}")
        print(f"    - Total repairs: {repair_results.get('total_repairs', 0)}")
        
        verify_results = results['stages'].get('verify', {}).get('summary', {})
        print(f"\n  Stage 4 - Verify:")
        print(f"    - Total files: {verify_results.get('total_files', 0)}")
        print(f"    - Passed: {verify_results.get('passed', 0)}")
        print(f"    - Failed: {verify_results.get('failed', 0)}")
        
        print(f"\n  Errors: {results.get('errors', [])}")
        print(f"  Total time: {results.get('total_time', 0)}s")
        
        return results
        
    except Exception as e:
        print(f"✗ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n🔍 DEBUGGING CodeAid MULTI-LANGUAGE SUPPORT")
    print("Testing on: https://github.com/kushwanth1806/Backend-api\n")
    
    # Test 1: Loading
    repo_data = test_loading()
    
    if not repo_data:
        sys.exit(1)
    
    # Test 2: Scanning  
    issues = test_scanning(repo_data)
    
    # Test 3: Full pipeline
    test_full_pipeline("https://github.com/kushwanth1806/Backend-api")
    
    print("\n" + "=" * 80)
    print("DEBUGGING COMPLETE")
    print("=" * 80)
