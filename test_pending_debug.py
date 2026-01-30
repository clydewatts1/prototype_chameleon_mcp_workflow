"""
Test to see the actual error from pending endpoint
"""
from fastapi.testclient import TestClient
from chameleon_workflow_engine.server import app

def test_pending_error():
    """Get detailed error from pending endpoint"""
    client = TestClient(app)
    
    response = client.get("/api/interventions/pending?limit=10&offset=0")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_pending_error()
