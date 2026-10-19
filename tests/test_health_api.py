"""
Automated unit tests for FastAPI Health API endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "TechSift AI"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
