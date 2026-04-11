#!/usr/bin/env python3
"""
CodeAID Integration Tests
Tests all API endpoints and features including CodeXGLUE evaluation
"""

import requests
import json
import sys
import time
from pathlib import Path

API_URL = "http://localhost:5001/api"
TIMEOUT = 120  # 2 minutes timeout for evaluation

def test_health():
    """Test health endpoint"""
    print("🧪 Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['status'] == 'healthy', f"Expected healthy status, got {data['status']}"
        print("✓ Health check passed")
        print(f"  - Service: {data['service']}")
        print(f"  - Version: {data['version']}")
        print(f"  - LLM Available: {data['llm_available']}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_status():
    """Test status endpoint"""
    print("\n🧪 Testing status endpoint...")
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        assert response.status_code == 200
        data = response.json()
        print("✓ Status check passed")
        print(f"  - LLM Provider: {data['llm_provider']}")
        print(f"  - API Key Configured: {data['api_key_configured']}")
        print(f"  - Upload Limit: {data['upload_limit_mb']}MB")
        return True
    except Exception as e:
        print(f"✗ Status check failed: {e}")
        return False


def test_codexglue_evaluation():
    """Test CodeXGLUE evaluation feature"""
    print("\n🧪 Testing CodeXGLUE evaluation (5 samples)...")
    try:
        payload = {"max_samples": 5}
        response = requests.post(
            f"{API_URL}/eval/codexglue",
            json=payload,
            timeout=TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert 'aggregate_metrics' in data
        assert 'per_sample_results' in data
        assert 'samples_evaluated' in data
        assert 'source' in data
        
        metrics = data['aggregate_metrics']
        print("✓ CodeXGLUE evaluation passed")
        print(f"  - Samples Evaluated: {data['samples_evaluated']}")
        print(f"  - Dataset Source: {data['source']}")
        print(f"  - Precision: {metrics.get('precision', 0):.1%}")
        print(f"  - Recall: {metrics.get('recall', 0):.1%}")
        print(f"  - F1 Score: {metrics.get('f1', 0):.1%}")
        print(f"  - Total TP: {data.get('total_tp', 0)}")
        print(f"  - Total FP: {data.get('total_fp', 0)}")
        print(f"  - Total FN: {data.get('total_fn', 0)}")
        
        # Print per-sample results
        print("\n  Per-Sample Results:")
        for sample in data.get('per_sample_results', [])[:3]:  # Show first 3
            print(f"    - {sample['id']}: F1={sample['metrics'].get('f1', 0):.1%}, " +
                  f"TP={sample['tp']}, FP={sample['fp']}, FN={sample['fn']}")
        
        return True
    except requests.exceptions.Timeout:
        print(f"✗ CodeXGLUE evaluation timed out (>{TIMEOUT}s)")
        return False
    except Exception as e:
        print(f"✗ CodeXGLUE evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_github_analyze_validation():
    """Test GitHub analysis validation (don't actually run, just test validation)"""
    print("\n🧪 Testing GitHub analysis endpoint validation...")
    try:
        # Test missing URL
        response = requests.post(
            f"{API_URL}/analyze/github",
            json={},
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400, "Should return 400 for missing URL"
        
        # Test invalid URL
        response = requests.post(
            f"{API_URL}/analyze/github",
            json={"url": "https://invalid.com/repo"},
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400, "Should return 400 for invalid GitHub URL"
        
        print("✓ GitHub analysis validation passed")
        return True
    except Exception as e:
        print(f"✗ GitHub analysis validation failed: {e}")
        return False


def test_llm_config():
    """Test LLM configuration endpoint"""
    print("\n🧪 Testing LLM configuration endpoints...")
    try:
        # Test GET config
        response = requests.get(f"{API_URL}/config/llm", timeout=5)
        assert response.status_code == 200
        data = response.json()
        print("✓ Get LLM config passed")
        print(f"  - Current Provider: {data['provider']}")
        print(f"  - API Key Configured: {data['api_key_configured']}")
        
        # Test POST config (without actual API key, just validation)
        response = requests.post(
            f"{API_URL}/config/llm",
            json={"provider": "anthropic", "api_key": ""},
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 200
        print("✓ Set LLM config passed")
        
        return True
    except Exception as e:
        print(f"✗ LLM config test failed: {e}")
        return False


def test_error_handling():
    """Test error handling"""
    print("\n🧪 Testing error handling...")
    try:
        # Test 404
        response = requests.get(f"{API_URL}/nonexistent", timeout=5)
        assert response.status_code == 404
        
        # Test invalid POST data
        response = requests.post(
            f"{API_URL}/eval/codexglue",
            data="invalid json",
            timeout=5
        )
        assert response.status_code == 400 or response.status_code == 500
        
        print("✓ Error handling passed")
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 CodeAID API Integration Tests")
    print("="*60)
    
    # Wait for API to be ready
    print("\n⏳ Waiting for API to be ready...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            requests.get(f"{API_URL}/health", timeout=2)
            print("✓ API is ready")
            break
        except:
            if i < 29:
                time.sleep(1)
            else:
                print("✗ API is not responding. Make sure Flask is running on port 5001")
                return False
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Status Check", test_status()))
    results.append(("GitHub Validation", test_github_analyze_validation()))
    results.append(("LLM Config", test_llm_config()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("CodeXGLUE Evaluation", test_codexglue_evaluation()))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
