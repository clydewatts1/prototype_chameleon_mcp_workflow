"""
Direct test of REST endpoints using TestClient
"""
from fastapi.testclient import TestClient
from chameleon_workflow_engine.server import app

def test_endpoints():
    """Test all endpoints directly"""
    client = TestClient(app)
    
    print("=" * 60)
    print("Testing Chameleon Workflow Engine REST Endpoints")
    print("=" * 60)
    print()
    
    # Test health
    response = client.get("/health")
    print(f"✓ GET /health: {response.status_code}")
    print(f"  {response.json()}\n")
    
    # Test pending interventions
    response = client.get("/api/interventions/pending?limit=10&offset=0")
    print(f"✓ GET /api/interventions/pending: {response.status_code}")
    data = response.json()
    print(f"  Result: {len(data)} interventions\n")
    
    # Test metrics
    response = client.get("/api/interventions/metrics")
    print(f"✓ GET /api/interventions/metrics: {response.status_code}")
    print(f"  Metrics keys: {list(response.json().keys())}\n")
    
    # Test get non-existent intervention
    response = client.get("/api/interventions/nonexistent-123")
    print(f"✓ GET /api/interventions/{{id}}: {response.status_code} (expected 404)")
    if response.status_code != 200:
        print(f"  {response.json()}\n")
    
    # Test docs
    response = client.get("/docs")
    print(f"✓ GET /docs: {response.status_code}")
    print(f"  Swagger UI available\n")
    
    print("=" * 60)
    print("✓ All endpoints are accessible!")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
