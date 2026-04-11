#!/usr/bin/env python3
"""
Production Smoke Test
Validates that all core components load and function correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all modules import successfully."""
    print("Testing imports...")
    
    try:
        from core.agents.coordinator import run_pipeline
        print("  ✅ Coordinator")
    except Exception as e:
        print(f"  ❌ Coordinator: {e}")
        return False
    
    try:
        from core.agents.scanner import scan_file
        print("  ✅ Scanner")
    except Exception as e:
        print(f"  ❌ Scanner: {e}")
        return False
    
    try:
        from core.agents.repair import repair_issues
        print("  ✅ Repair")
    except Exception as e:
        print(f"  ❌ Repair: {e}")
        return False
    
    try:
        from core.agents.explain import explain_issues
        print("  ✅ Explain")
    except Exception as e:
        print(f"  ❌ Explain: {e}")
        return False
    
    try:
        from core.repo_loader import load_repository
        print("  ✅ Repository Loader")
    except Exception as e:
        print(f"  ❌ Repository Loader: {e}")
        return False
    
    try:
        from utils.codexglue_loader import run_evaluation
        print("  ✅ CodeXGLUE Loader")
    except Exception as e:
        print(f"  ❌ CodeXGLUE Loader: {e}")
        return False
    
    try:
        from api import app
        print("  ✅ Flask App")
    except Exception as e:
        print(f"  ❌ Flask App: {e}")
        return False
    
    return True


def test_api_routes():
    """Test that all required API routes are registered."""
    print("\nTesting API routes...")
    
    try:
        from api import app
        
        routes = {str(rule) for rule in app.url_map.iter_rules()}
        
        required_endpoints = [
            '/api/health',
            '/api/status',
            '/api/analyze/github',
            '/api/analyze/upload',
            '/api/overview',
            '/api/eval/codexglue',
        ]
        
        all_found = True
        for endpoint in required_endpoints:
            # Check if endpoint route exists (accounting for different formats)
            found = any(endpoint in str(rule) for rule in app.url_map.iter_rules())
            
            if found:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} NOT FOUND")
                all_found = False
        
        return all_found
    
    except Exception as e:
        print(f"  ❌ Error testing routes: {e}")
        return False


def test_scanner():
    """Test that the scanner can process code."""
    print("\nTesting scanner...")
    
    try:
        from core.agents.scanner import scan_file
        
        # Test with simple Python code
        test_code = {
            "content": """import os
import sys

def test():
    x = 1
    return x
""",
            "language": "python",
            "relative_path": "test.py"
        }
        
        result = scan_file(test_code)
        
        if "issues" in result:
            print(f"  ✅ Scanner found {len(result['issues'])} issues")
            return True
        else:
            print("  ⚠️  Scanner returned no issues field")
            return False
    
    except Exception as e:
        print(f"  ❌ Scanner error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluation():
    """Test that evaluation can run."""
    print("\nTesting evaluation...")
    
    try:
        from utils.codexglue_loader import run_evaluation
        
        # Run evaluation without repo files (uses CodeXGLUE samples)
        result = run_evaluation(max_samples=1, repo_files=None)
        
        required_fields = [
            'source',
            'samples_evaluated',
            'aggregate_metrics',
            'total_tp',
            'total_fp',
            'total_fn',
            'per_sample_results',
            'per_type_metrics'
        ]
        
        all_found = True
        for field in required_fields:
            if field in result:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ Missing {field}")
                all_found = False
        
        return all_found
    
    except Exception as e:
        print(f"  ❌ Evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Production Smoke Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("API Routes", test_api_routes),
        ("Scanner", test_scanner),
        ("Evaluation", test_evaluation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
