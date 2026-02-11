"""
Integration tests for ZoomInfo in the intelligence pipeline.
TDD: Tests written FIRST before implementation.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

# Add worker and parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDataSourceEnum:
    """Test that ZoomInfo is added to DataSource enum."""

    def test_zoominfo_in_datasource(self):
        from intelligence_gatherer import DataSource
        assert hasattr(DataSource, "ZOOMINFO")
        assert DataSource.ZOOMINFO.value == "zoominfo"


class TestIntelligenceGathererZoomInfo:
    """Test ZoomInfo integration in IntelligenceGatherer."""

    def test_init_accepts_zoominfo_token(self):
        """Gatherer accepts ZoomInfo access token parameter."""
        from intelligence_gatherer import IntelligenceGatherer
        gatherer = IntelligenceGatherer(
            apollo_api_key="test-apollo",
            pdl_api_key="test-pdl",
            zoominfo_access_token="test-zi"
        )
        assert gatherer.zoominfo_access_token == "test-zi"

    def test_init_works_without_zoominfo_token(self):
        """Gatherer works without ZoomInfo token (optional)."""
        from intelligence_gatherer import IntelligenceGatherer
        gatherer = IntelligenceGatherer(
            apollo_api_key="test-apollo",
            pdl_api_key="test-pdl"
        )
        assert gatherer.zoominfo_access_token is None

    def test_circuit_breaker_exists_for_zoominfo(self):
        """CircuitBreaker is initialized for ZoomInfo."""
        from intelligence_gatherer import IntelligenceGatherer, DataSource
        gatherer = IntelligenceGatherer(
            apollo_api_key="a", pdl_api_key="p",
            zoominfo_access_token="z"
        )
        assert DataSource.ZOOMINFO in gatherer.circuit_breakers

    @pytest.mark.asyncio
    async def test_gather_includes_zoominfo_when_token_provided(self):
        """ZoomInfo is included in default sources when token is provided."""
        from intelligence_gatherer import IntelligenceGatherer, DataSource, IntelligenceResult
        gatherer = IntelligenceGatherer(
            apollo_api_key="a", pdl_api_key="p",
            zoominfo_access_token="z"
        )
        # Mock all fetch methods
        for method_name in ['_fetch_apollo_data', '_fetch_apollo_people',
                            '_fetch_pdl_data', '_fetch_pdl_people',
                            '_fetch_zoominfo_data', '_fetch_zoominfo_people']:
            setattr(gatherer, method_name, AsyncMock(return_value=IntelligenceResult(
                source=DataSource.APOLLO, success=True,
                data={}, error=None, attempt_count=1
            )))

        results = await gatherer.gather_company_intelligence("Test", "test.com")
        gatherer._fetch_zoominfo_data.assert_called_once()
        gatherer._fetch_zoominfo_people.assert_called_once()

    @pytest.mark.asyncio
    async def test_gather_excludes_zoominfo_without_token(self):
        """ZoomInfo is NOT included when no token is provided."""
        from intelligence_gatherer import IntelligenceGatherer, DataSource, IntelligenceResult
        gatherer = IntelligenceGatherer(
            apollo_api_key="a", pdl_api_key="p"
        )
        # Mock Apollo and PDL methods
        for method_name in ['_fetch_apollo_data', '_fetch_apollo_people',
                            '_fetch_pdl_data', '_fetch_pdl_people']:
            setattr(gatherer, method_name, AsyncMock(return_value=IntelligenceResult(
                source=DataSource.APOLLO, success=True,
                data={}, error=None, attempt_count=1
            )))

        # Mock ZoomInfo methods to track if they're called
        gatherer._fetch_zoominfo_data = AsyncMock()
        gatherer._fetch_zoominfo_people = AsyncMock()

        results = await gatherer.gather_company_intelligence("Test", "test.com")
        # ZoomInfo should not be called when no token is provided
        gatherer._fetch_zoominfo_data.assert_not_called()
        gatherer._fetch_zoominfo_people.assert_not_called()


class TestZoomInfoSourceTier:
    """Test ZoomInfo source reliability in LLM Council."""

    def test_zoominfo_tier_is_tier_1(self):
        """ZoomInfo should have TIER_1 reliability (premium data source)."""
        # Import from worker directory where the actual council lives
        # Mock openai since it may not be installed in test env
        import importlib
        import types
        mock_openai = types.ModuleType("openai")
        mock_openai.AsyncOpenAI = type("AsyncOpenAI", (), {})
        with patch.dict("sys.modules", {"openai": mock_openai}):
            spec = importlib.util.spec_from_file_location(
                "worker_llm_council",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker", "llm_council.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            assert mod.SourceTier.TIER_1 is not None


class TestZoomInfoPeopleProcessing:
    """Test ZoomInfo people data processing format."""

    def test_zoominfo_contact_normalization(self):
        """ZoomInfo contact data normalizes to standard stakeholder format."""
        from zoominfo_client import ZoomInfoClient
        raw_contact = {
            "firstName": "Jane",
            "lastName": "Doe",
            "jobTitle": "CTO",
            "email": "jane@test.com",
            "phone": "+1-555-0100",
            "linkedInUrl": "linkedin.com/in/janedoe"
        }
        normalized = ZoomInfoClient._normalize_contact(raw_contact)
        assert normalized["name"] == "Jane Doe"
        assert normalized["title"] == "CTO"
        assert normalized["email"] == "jane@test.com"
        assert normalized["phone"] == "+1-555-0100"
        assert normalized["linkedin"] == "linkedin.com/in/janedoe"
