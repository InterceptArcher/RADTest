"""
Tests for debug endpoints.
Features 018-021: Debug Mode API Tests
Following TDD - tests written to verify debug functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock settings before importing app
mock_settings = MagicMock()
mock_settings.app_name = "RADTest Backend"
mock_settings.debug = False
mock_settings.max_request_size = 1_048_576

with patch.dict('os.environ', {
    'RAILWAY_WORKER_URL': 'http://mock-worker',
    'RAILWAY_API_TOKEN': 'mock-token',
    'RAILWAY_PROJECT_ID': 'mock-project',
    'RAILWAY_ENVIRONMENT_ID': 'mock-env',
    'RAILWAY_SERVICE_ID': 'mock-service',
    'SUPABASE_URL': 'http://mock-supabase',
    'SUPABASE_KEY': 'mock-key',
    'APOLLO_API_KEY': 'mock-apollo',
    'PDL_API_KEY': 'mock-pdl',
    'OPENAI_API_KEY': 'mock-openai',
    'GAMMA_API_KEY': 'mock-gamma',
}):
    from main import app

client = TestClient(app)


class TestDebugEndpoints:
    """Test suite for debug endpoints."""

    def test_get_debug_data_success(self):
        """Test successful retrieval of debug data."""
        response = client.get("/debug-data/job-123")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "job_id" in data
        assert "company_name" in data
        assert "domain" in data
        assert "status" in data
        assert "process_steps" in data
        assert "api_responses" in data
        assert "llm_thought_processes" in data
        assert "process_flow" in data
        assert "created_at" in data

    def test_get_debug_data_not_found(self):
        """Test 404 for non-existent job."""
        response = client.get("/debug-data/invalid-job-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_check_debug_data_available(self):
        """Test HEAD request for debug data availability."""
        response = client.head("/debug-data/job-123")

        assert response.status_code == 200

    def test_check_debug_data_not_available(self):
        """Test HEAD request for unavailable debug data."""
        response = client.head("/debug-data/invalid-job-id")

        assert response.status_code == 404

    def test_get_process_steps_success(self):
        """Test successful retrieval of process steps."""
        response = client.get("/debug-data/job-123/process-steps")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Verify step structure
        step = data[0]
        assert "id" in step
        assert "name" in step
        assert "description" in step
        assert "status" in step

    def test_get_process_steps_not_found(self):
        """Test 404 for process steps of non-existent job."""
        response = client.get("/debug-data/invalid-job-id/process-steps")

        assert response.status_code == 404

    def test_get_api_responses_success(self):
        """Test successful retrieval of API responses."""
        response = client.get("/debug-data/job-123/api-responses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Verify response structure
        api_response = data[0]
        assert "id" in api_response
        assert "api_name" in api_response
        assert "url" in api_response
        assert "method" in api_response
        assert "status_code" in api_response
        assert "response_body" in api_response

    def test_get_api_responses_with_masking(self):
        """Test API responses with sensitive data masking enabled."""
        response = client.get("/debug-data/job-123/api-responses?mask_sensitive=true")

        assert response.status_code == 200
        data = response.json()

        # Verify masking is applied
        for api_response in data:
            if api_response.get("is_sensitive"):
                assert "masked_fields" in api_response

    def test_get_api_responses_without_masking(self):
        """Test API responses with sensitive data masking disabled."""
        response = client.get("/debug-data/job-123/api-responses?mask_sensitive=false")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_get_api_responses_not_found(self):
        """Test 404 for API responses of non-existent job."""
        response = client.get("/debug-data/invalid-job-id/api-responses")

        assert response.status_code == 404

    def test_get_llm_thought_processes_success(self):
        """Test successful retrieval of LLM thought processes."""
        response = client.get("/debug-data/job-123/llm-processes")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Verify thought process structure
        process = data[0]
        assert "id" in process
        assert "task_name" in process
        assert "model" in process
        assert "steps" in process
        assert "final_decision" in process

        # Verify steps structure
        if process["steps"]:
            step = process["steps"][0]
            assert "id" in step
            assert "step" in step
            assert "action" in step
            assert "reasoning" in step

    def test_get_llm_thought_processes_not_found(self):
        """Test 404 for LLM processes of non-existent job."""
        response = client.get("/debug-data/invalid-job-id/llm-processes")

        assert response.status_code == 404

    def test_get_process_flow_success(self):
        """Test successful retrieval of process flow."""
        response = client.get("/debug-data/job-123/process-flow")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

        # Verify node structure
        if data["nodes"]:
            node = data["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "status" in node

        # Verify edge structure
        if data["edges"]:
            edge = data["edges"][0]
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge

    def test_get_process_flow_not_found(self):
        """Test 404 for process flow of non-existent job."""
        response = client.get("/debug-data/invalid-job-id/process-flow")

        assert response.status_code == 404

    def test_debug_data_contains_all_features(self):
        """Test that debug data includes all required features (018-021)."""
        response = client.get("/debug-data/job-123")

        assert response.status_code == 200
        data = response.json()

        # Feature 018: Process Inspection
        assert len(data["process_steps"]) > 0
        for step in data["process_steps"]:
            assert step["status"] in ["pending", "in_progress", "completed", "failed"]

        # Feature 019: API Return Values
        assert len(data["api_responses"]) > 0
        for api_resp in data["api_responses"]:
            assert "status_code" in api_resp
            assert "response_body" in api_resp

        # Feature 020: LLM Thought Process
        assert len(data["llm_thought_processes"]) > 0
        for llm_proc in data["llm_thought_processes"]:
            assert "steps" in llm_proc
            assert "final_decision" in llm_proc

        # Feature 021: Process Flow Visualization
        assert "nodes" in data["process_flow"]
        assert "edges" in data["process_flow"]
        assert len(data["process_flow"]["nodes"]) > 0

    def test_process_flow_has_correct_node_types(self):
        """Test that process flow includes various node types."""
        response = client.get("/debug-data/job-123/process-flow")

        assert response.status_code == 200
        data = response.json()

        node_types = {node["type"] for node in data["nodes"]}

        # Should have at least start, end, and some process nodes
        assert "start" in node_types
        assert "end" in node_types
        # Should have API and/or LLM nodes
        assert "api" in node_types or "llm" in node_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
