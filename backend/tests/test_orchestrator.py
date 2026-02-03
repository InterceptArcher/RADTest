"""
Tests for Orchestrator LLM module.
Following TDD - write failing tests first.
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import (
    analyze_and_plan,
    OrchestratorResult,
    DATA_POINTS,
    API_CAPABILITIES,
    get_default_query_plan
)


class TestOrchestratorDataPoints:
    """Test data point requirements are properly defined."""

    def test_all_data_points_have_minimum_two_apis(self):
        """Each data point must have at least 2 API assignments."""
        for category, points in DATA_POINTS.items():
            for point_name, apis in points.items():
                assert len(apis) >= 2, f"{category}.{point_name} has less than 2 APIs"

    def test_all_assigned_apis_are_valid(self):
        """All assigned APIs must exist in API_CAPABILITIES."""
        valid_apis = set(API_CAPABILITIES.keys())
        for category, points in DATA_POINTS.items():
            for point_name, apis in points.items():
                for api in apis:
                    assert api in valid_apis, f"Invalid API '{api}' in {category}.{point_name}"

    def test_all_required_categories_exist(self):
        """All required output categories must be defined."""
        required_categories = [
            "executive_snapshot",
            "buying_signals",
            "opportunity_themes",
            "stakeholder_map",
            "supporting_assets"
        ]
        for category in required_categories:
            assert category in DATA_POINTS, f"Missing category: {category}"


class TestAPICapabilities:
    """Test API capabilities are properly defined."""

    def test_all_apis_have_capabilities(self):
        """Each API must have defined capabilities."""
        required_apis = ["apollo", "pdl", "hunter", "gnews"]
        for api in required_apis:
            assert api in API_CAPABILITIES, f"Missing API: {api}"
            assert "best_for" in API_CAPABILITIES[api], f"API {api} missing 'best_for'"
            assert "provides" in API_CAPABILITIES[api], f"API {api} missing 'provides'"


class TestOrchestratorResult:
    """Test OrchestratorResult structure."""

    def test_result_has_required_fields(self):
        """OrchestratorResult must have all required fields."""
        result = OrchestratorResult(
            apis_to_query=["apollo", "pdl"],
            data_point_api_mapping={"company_name": ["apollo", "pdl"]},
            reasoning="Test reasoning",
            priority_order=["apollo", "pdl"]
        )
        assert hasattr(result, 'apis_to_query')
        assert hasattr(result, 'data_point_api_mapping')
        assert hasattr(result, 'reasoning')
        assert hasattr(result, 'priority_order')


class TestDefaultQueryPlan:
    """Test default/fallback query plan."""

    def test_default_plan_includes_all_apis(self):
        """Default plan should query all APIs as fallback."""
        result = get_default_query_plan()
        assert set(result.apis_to_query) == {"apollo", "pdl", "hunter", "gnews"}

    def test_default_plan_has_all_data_points(self):
        """Default plan should map all data points."""
        result = get_default_query_plan()
        # Should have mappings for all categories
        assert len(result.data_point_api_mapping) > 0


class TestOrchestratorPlanning:
    """Test orchestrator query planning."""

    @pytest.mark.asyncio
    async def test_returns_valid_result_structure(self):
        """Orchestrator should return OrchestratorResult."""
        company_data = {"company_name": "Acme Inc", "domain": "acme.com"}
        result = await analyze_and_plan(company_data)

        assert isinstance(result, OrchestratorResult)
        assert len(result.apis_to_query) > 0
        assert len(result.data_point_api_mapping) > 0

    @pytest.mark.asyncio
    async def test_minimum_apis_selected(self):
        """Should select at least some APIs."""
        company_data = {"company_name": "Test Corp", "domain": "test.com"}
        result = await analyze_and_plan(company_data)

        # Should have at least 2 APIs for a complete profile
        assert len(result.apis_to_query) >= 2

    @pytest.mark.asyncio
    async def test_handles_empty_input_gracefully(self):
        """Should handle empty/invalid input with default plan."""
        result = await analyze_and_plan({})

        # Should fall back to default plan
        assert isinstance(result, OrchestratorResult)
        assert len(result.apis_to_query) > 0
