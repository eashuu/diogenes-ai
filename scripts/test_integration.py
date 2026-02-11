#!/usr/bin/env python3
"""
Test script to verify frontend-backend integration.
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000/api"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/v1/health/")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Health check passed: {data}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_research():
    """Test research endpoint (non-streaming)"""
    print("\nTesting research endpoint...")
    try:
        payload = {
            "query": "What is Python?",
            "mode": "quick"
        }
        response = requests.post(
            f"{API_BASE}/v1/research/",
            json=payload,
            params={"profile": "general"}
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Research completed:")
        print(f"  - Session ID: {data.get('session_id')}")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Sources: {len(data.get('sources', []))}")
        if data.get('answer'):
            answer_preview = data['answer']['content'][:100] + "..."
            print(f"  - Answer: {answer_preview}")
        return True
    except Exception as e:
        print(f"✗ Research failed: {e}")
        return False

def test_cors():
    """Test CORS headers"""
    print("\nTesting CORS configuration...")
    try:
        response = requests.options(
            f"{API_BASE}/v1/research/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )
        cors_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower().startswith('access-control')
        }
        if cors_headers:
            print(f"✓ CORS headers present: {cors_headers}")
            return True
        else:
            print("✗ No CORS headers found")
            return False
    except Exception as e:
        print(f"✗ CORS test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Diogenes Frontend-Backend Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test health
    results.append(("Health Check", test_health()))
    
    # Test research
    results.append(("Research API", test_research()))
    
    # Test CORS
    results.append(("CORS Configuration", test_cors()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    print("=" * 60)
    if all_passed:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed. Please check the backend server.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
