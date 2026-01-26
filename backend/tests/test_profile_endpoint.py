"""
Test module for profile request endpoint.
Following TDD approach - tests written before implementation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json


@pytest.fixture
def client():
    """
    Fixture to create test client.
    This will fail until main app is implemented.
    """
    from src.main import app
    return TestClient(app)


@pytest.fixture
def valid_company_data():
    """Sample valid company data for testing."""
    return {
        "company_name": "Acme Corp",
        "domain": "acme.com",
        "industry": "Technology",
        "requested_by": "user@example.com"
    }


@pytest.fixture
def invalid_company_data():
    """Sample invalid company data (missing required fields)."""
    return {
        "company_name": "Incomplete Corp"
    }


class TestProfileRequestEndpoint:
    """Test cases for /profile-request endpoint."""

    def test_endpoint_exists(self, client):
        """Test that the /profile-request endpoint exists."""
        response = client.post("/profile-request", json={"test": "data"})
        # Should not return 404
        assert response.status_code != 404

    def test_accepts_post_only(self, client):
        """Test that endpoint only accepts POST requests."""
        response = client.get("/profile-request")
        assert response.status_code == 405  # Method Not Allowed

    def test_accepts_valid_json(self, client, valid_company_data):
        """Test that endpoint accepts valid JSON payload."""
        with patch('src.services.railway_client.forward_to_worker') as mock_forward:
            mock_forward.return_value = {"status": "success", "job_id": "123"}
            response = client.post("/profile-request", json=valid_company_data)
            assert response.status_code == 200
            assert "job_id" in response.json()

    def test_rejects_invalid_json(self, client):
        """Test that endpoint returns 400 for invalid JSON."""
        response = client.post(
            "/profile-request",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400

    def test_validates_required_fields(self, client, invalid_company_data):
        """Test that endpoint validates required fields."""
        response = client.post("/profile-request", json=invalid_company_data)
        assert response.status_code == 422  # Unprocessable Entity
        error_detail = response.json()
        assert "detail" in error_detail

    def test_forwards_data_to_railway_worker(self, client, valid_company_data):
        """Test that endpoint forwards data to Railway worker service."""
        with patch('src.services.railway_client.forward_to_worker') as mock_forward:
            mock_forward.return_value = {"status": "success", "job_id": "test-123"}

            response = client.post("/profile-request", json=valid_company_data)

            # Verify the forward function was called with correct data
            mock_forward.assert_called_once()
            call_args = mock_forward.call_args[0][0]
            assert call_args["company_name"] == valid_company_data["company_name"]
            assert call_args["domain"] == valid_company_data["domain"]

    def test_handles_network_errors(self, client, valid_company_data):
        """Test that endpoint handles network errors gracefully."""
        with patch('src.services.railway_client.forward_to_worker') as mock_forward:
            mock_forward.side_effect = ConnectionError("Network error")

            response = client.post("/profile-request", json=valid_company_data)

            assert response.status_code == 503  # Service Unavailable
            error_detail = response.json()
            assert "error" in error_detail

    def test_handles_worker_api_errors(self, client, valid_company_data):
        """Test that endpoint handles Railway worker API errors."""
        with patch('src.services.railway_client.forward_to_worker') as mock_forward:
            mock_forward.side_effect = Exception("Worker API error")

            response = client.post("/profile-request", json=valid_company_data)

            assert response.status_code == 500
            error_detail = response.json()
            assert "error" in error_detail

    def test_returns_job_id_on_success(self, client, valid_company_data):
        """Test that endpoint returns job ID on successful submission."""
        with patch('src.services.railway_client.forward_to_worker') as mock_forward:
            expected_job_id = "job-xyz-789"
            mock_forward.return_value = {
                "status": "success",
                "job_id": expected_job_id
            }

            response = client.post("/profile-request", json=valid_company_data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["job_id"] == expected_job_id
            assert response_data["status"] == "success"

    def test_rejects_oversized_payloads(self, client):
        """Test that endpoint rejects excessively large payloads."""
        # Create a large payload (> 1MB)
        large_data = {
            "company_name": "Test Corp",
            "domain": "test.com",
            "large_field": "x" * (2 * 1024 * 1024)  # 2MB of data
        }

        response = client.post("/profile-request", json=large_data)
        assert response.status_code == 413  # Payload Too Large
