"""
Quick test script to verify REST endpoints while server is running.
Run this in a separate terminal while the server is running.
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✓ Health: {response.status_code}")
        print(f"  {response.json()}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health: {e}\n")
        return False

def test_pending_interventions():
    """Test get pending interventions endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/interventions/pending?limit=10&offset=0")
        print(f"✓ GET /api/interventions/pending: {response.status_code}")
        data = response.json()
        print(f"  Pending interventions count: {len(data)}")
        print(f"  Sample: {json.dumps(data[:1] if data else [], indent=2)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ GET /api/interventions/pending: {e}\n")
        return False

def test_metrics():
    """Test get metrics endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/interventions/metrics")
        print(f"✓ GET /api/interventions/metrics: {response.status_code}")
        data = response.json()
        print(f"  {json.dumps(data, indent=2)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ GET /api/interventions/metrics: {e}\n")
        return False

def test_get_intervention():
    """Test get specific intervention endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/interventions/nonexistent-123")
        print(f"✓ GET /api/interventions/{{id}}: {response.status_code}")
        if response.status_code == 404:
            print(f"  Expected 404 for non-existent ID: {response.json()}\n")
        else:
            print(f"  {response.json()}\n")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"✗ GET /api/interventions/{{id}}: {e}\n")
        return False

def test_docs():
    """Test API documentation endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✓ GET /docs: {response.status_code}")
        print(f"  Swagger UI available at: {BASE_URL}/docs\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ GET /docs: {e}\n")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Chameleon Workflow Engine REST Endpoints")
    print("=" * 60)
    print()
    
    # Wait a moment for server to be ready
    sleep(1)
    
    results = {
        "Health": test_health(),
        "Pending Interventions": test_pending_interventions(),
        "Metrics": test_metrics(),
        "Get Intervention": test_get_intervention(),
        "Documentation": test_docs(),
    }
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All endpoints are working correctly!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")
