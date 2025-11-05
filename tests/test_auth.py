"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_request_otp_invalid_phone():
    """Test OTP request with invalid phone"""
    response = client.post("/api/auth/register/request-otp", json={"phone": "123"})
    assert response.status_code == 400


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["version"] == "2.0"

