import pytest
from tests.conftest import test_client

class TestAuthentication:
    def test_successful_login(self, test_client, admin_credentials):
        response = test_client.post("/auth/login", json=admin_credentials)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_failed_login(self, test_client):
        response = test_client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_protected_endpoint_without_authentication(self, test_client):
        response = test_client.get("/alerts")

        assert response.status_code == 401

    def test_protected_endpoint_with_authentication(self, test_client, auth_headers):
        response = test_client.get("/alerts", headers=auth_headers)

        assert response.status_code == 200