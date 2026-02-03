"""
Tests for Orchestrator LLM module - Granular Version.
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
    GRANULAR_DATA_POINTS,
    API_CAPABILITIES,
    get_default_query_plan,
    should_query_api,
    get_apis_for_field
)


class TestGranularDataPoints:
    """Test granular data point requirements are properly defined."""

    def test_all_data_points_have_minimum_two_apis(self):
        """Each data point must have at least 2 API assignments."""
        for field_path, apis in GRANULAR_DATA_POINTS.items():
            assert len(apis) >= 2, f"{field_path} has less than 2 APIs: {apis}"

    def test_all_assigned_apis_are_valid(self):
        """All assigned APIs must exist in API_CAPABILITIES."""
        valid_apis = set(API_CAPABILITIES.keys())
        for field_path, apis in GRANULAR_DATA_POINTS.items():
            for api in apis:
                assert api in valid_apis, f"Invalid API '{api}' in {field_path}"

    def test_all_required_sections_exist(self):
        """All required output sections must have fields defined."""
        required_sections = [
            "executive_snapshot",
            "buying_signals",
            "opportunity_themes",
            "stakeholder_map",
            "supporting_assets",
            "news_intelligence"
        ]
        sections_found = set()
        for field_path in GRANULAR_DATA_POINTS.keys():
            section = field_path.split(".")[0]
            sections_found.add(section)

        for section in required_sections:
            assert section in sections_found, f"Missing section: {section}"

    def test_stakeholder_email_fields_include_hunter(self):
        """All stakeholder email fields must include Hunter.io."""
        email_fields = [key for key in GRANULAR_DATA_POINTS.keys() if "_email" in key]
        for field in email_fields:
            apis = GRANULAR_DATA_POINTS[field]
            assert "hunter" in apis, f"{field} must include 'hunter' API"

    def test_news_fields_include_gnews(self):
        """All news intelligence fields must include GNews."""
        news_fields = [key for key in GRANULAR_DATA_POINTS.keys() if key.startswith("news_intelligence.")]
        for field in news_fields:
            apis = GRANULAR_DATA_POINTS[field]
            assert "gnews" in apis, f"{field} must include 'gnews' API"


class TestAPICapabilities:
    """Test API capabilities are properly defined."""

    def test_all_apis_have_capabilities(self):
        """Each API must have defined capabilities."""
        required_apis = ["apollo", "pdl", "hunter", "gnews"]
        for api in required_apis:
            assert api in API_CAPABILITIES, f"Missing API: {api}"
            assert "best_for" in API_CAPABILITIES[api], f"API {api} missing 'best_for'"
            assert "provides" in API_CAPABILITIES[api], f"API {api} missing 'provides'"

    def test_hunter_marked_as_required(self):
        """Hunter.io must be marked as required for stakeholder_map."""
        assert "required_for" in API_CAPABILITIES["hunter"]
        assert "stakeholder_map" in API_CAPABILITIES["hunter"]["required_for"]


class TestOrchestratorResult:
    """Test OrchestratorResult structure."""

    def test_result_has_required_fields(self):
        """OrchestratorResult must have all required fields."""
        result = OrchestratorResult(
            apis_to_query=["apollo", "pdl", "hunter", "gnews"],
            data_point_api_mapping={"executive_snapshot.company_overview": ["apollo", "pdl"]},
            reasoning="Test reasoning",
            priority_order=["apollo", "hunter", "pdl", "gnews"],
            granular_assignments={"executive_snapshot": {"company_overview": ["apollo", "pdl"]}}
        )
        assert hasattr(result, 'apis_to_query')
        assert hasattr(result, 'data_point_api_mapping')
        assert hasattr(result, 'reasoning')
        assert hasattr(result, 'priority_order')
        assert hasattr(result, 'granular_assignments')
        assert result.orchestrator_version == "2.0-granular"


class TestHunterAlwaysQueried:
    """Test that Hunter.io is ALWAYS queried."""

    def test_should_query_api_always_true_for_hunter(self):
        """should_query_api must return True for 'hunter' regardless of plan."""
        # Create a plan that doesn't explicitly include hunter
        plan = OrchestratorResult(
            apis_to_query=["apollo", "pdl"],  # No hunter
            data_point_api_mapping={},
            reasoning="Test",
            priority_order=["apollo", "pdl"],
            granular_assignments={}
        )
        # should_query_api must STILL return True for hunter
        assert should_query_api("hunter", plan) == True

    def test_default_plan_includes_hunter(self):
        """Default plan must include Hunter.io."""
        result = get_default_query_plan()
        assert "hunter" in result.apis_to_query

    def test_hunter_in_priority_order(self):
        """Hunter.io must be in the priority order."""
        result = get_default_query_plan()
        assert "hunter" in result.priority_order


class TestDefaultQueryPlan:
    """Test default/fallback query plan."""

    def test_default_plan_includes_all_apis(self):
        """Default plan should query all APIs as fallback."""
        result = get_default_query_plan()
        assert set(result.apis_to_query) == {"apollo", "pdl", "hunter", "gnews"}

    def test_default_plan_has_all_data_points(self):
        """Default plan should map all data points."""
        result = get_default_query_plan()
        # Should have mappings for all granular fields
        assert len(result.data_point_api_mapping) >= len(GRANULAR_DATA_POINTS)

    def test_default_plan_has_granular_assignments(self):
        """Default plan must have granular_assignments structure."""
        result = get_default_query_plan()
        assert len(result.granular_assignments) > 0
        assert "executive_snapshot" in result.granular_assignments
        assert "buying_signals" in result.granular_assignments
        assert "stakeholder_map" in result.granular_assignments


class TestGetApisForField:
    """Test field-level API retrieval."""

    def test_get_apis_for_known_field(self):
        """Should return APIs for a known field."""
        plan = get_default_query_plan()
        apis = get_apis_for_field("executive_snapshot.company_overview", plan)
        assert len(apis) >= 2

    def test_get_apis_for_stakeholder_email(self):
        """Should include hunter for stakeholder email fields."""
        plan = get_default_query_plan()
        apis = get_apis_for_field("stakeholder_map.cio_email", plan)
        assert "hunter" in apis

    def test_get_apis_for_unknown_field_returns_default(self):
        """Should return default APIs for unknown fields."""
        plan = get_default_query_plan()
        apis = get_apis_for_field("unknown.field", plan)
        assert len(apis) >= 2  # Should return default


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
    async def test_all_four_apis_selected(self):
        """Should select all 4 APIs since Hunter is always required."""
        company_data = {"company_name": "Test Corp", "domain": "test.com"}
        result = await analyze_and_plan(company_data)

        # Must have all 4 APIs since they're all required
        assert "apollo" in result.apis_to_query
        assert "hunter" in result.apis_to_query
        assert "pdl" in result.apis_to_query
        assert "gnews" in result.apis_to_query

    @pytest.mark.asyncio
    async def test_handles_empty_input_gracefully(self):
        """Should handle empty/invalid input with default plan."""
        result = await analyze_and_plan({})

        # Should fall back to default plan
        assert isinstance(result, OrchestratorResult)
        assert len(result.apis_to_query) == 4  # All APIs
        assert "hunter" in result.apis_to_query

    @pytest.mark.asyncio
    async def test_granular_assignments_in_result(self):
        """Result should include granular_assignments."""
        company_data = {"company_name": "Test Corp", "domain": "test.com"}
        result = await analyze_and_plan(company_data)

        assert hasattr(result, 'granular_assignments')
        assert len(result.granular_assignments) > 0
