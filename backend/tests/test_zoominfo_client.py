"""
Tests for ZoomInfo API client.
TDD: Tests written FIRST before implementation.
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Add worker directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker"))


class TestZoomInfoClientInit:
    """Test ZoomInfoClient initialization."""

    def test_init_with_access_token(self):
        """Client initializes with access token from parameter."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        assert client.access_token == "test-token"

    def test_init_from_env_variable(self):
        """Client reads ZOOMINFO_ACCESS_TOKEN from environment."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_ACCESS_TOKEN": "env-token"}):
            client = ZoomInfoClient()
            assert client.access_token == "env-token"

    def test_init_without_token_raises(self):
        """Client raises ValueError when no token is available."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="ZOOMINFO_ACCESS_TOKEN"):
                ZoomInfoClient()

    def test_default_timeout(self):
        """Client has a default 30s timeout."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test")
        assert client.timeout == 30

    def test_default_base_url(self):
        """Client uses correct ZoomInfo GTM base URL."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test")
        assert client.base_url == "https://api.zoominfo.com/gtm"

    def test_content_type_header(self):
        """Client sends application/vnd.api+json content type."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test")
        assert client.headers["Content-Type"] == "application/vnd.api+json"
        assert client.headers["Authorization"] == "Bearer test"


class TestZoomInfoRateLimiter:
    """Test rate limiter for 25 req/sec ZoomInfo limit."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        """Allows requests when under 25/sec."""
        from zoominfo_client import ZoomInfoRateLimiter
        limiter = ZoomInfoRateLimiter(max_per_second=25)
        assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_generates_unique_instances(self):
        """Each limiter tracks independently."""
        from zoominfo_client import ZoomInfoRateLimiter
        limiter1 = ZoomInfoRateLimiter(max_per_second=25)
        limiter2 = ZoomInfoRateLimiter(max_per_second=10)
        assert limiter1.max_per_second != limiter2.max_per_second


class TestCompanyEnrich:
    """Test ZoomInfo Company Enrich endpoint."""

    @pytest.mark.asyncio
    async def test_enrich_by_domain(self):
        """Enriches company by domain."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{
                "companyName": "Acme Corp",
                "domain": "acme.com",
                "employeeCount": 500,
                "revenue": 50000000,
                "industry": "Technology",
                "city": "San Francisco",
                "state": "California",
                "country": "US",
                "yearFounded": 2015
            }]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_company(domain="acme.com")
            assert result["success"] is True
            assert result["data"]["companyName"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_enrich_by_company_name(self):
        """Enriches company by name when domain not available."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {"data": [{"companyName": "Acme Corp", "domain": "acme.com"}]}
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_company(company_name="Acme Corp")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_enrich_handles_empty_response(self):
        """Returns failure when no company data found."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value={"data": []}):
            result = await client.enrich_company(domain="nonexistent.com")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_enrich_normalizes_to_standard_fields(self):
        """Company data is normalized to match Apollo/PDL field names."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{
                "companyName": "Test Corp",
                "employeeCount": 200,
                "revenue": 10000000,
                "industry": "Software",
                "city": "Austin",
                "state": "Texas",
                "yearFounded": 2010
            }]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_company(domain="test.com")
            normalized = result["normalized"]
            assert normalized["company_name"] == "Test Corp"
            assert normalized["employee_count"] == 200
            assert normalized["revenue"] == 10000000
            assert normalized["headquarters"] == "Austin, Texas"
            assert normalized["industry"] == "Software"
            assert normalized["founded_year"] == 2010


class TestContactSearch:
    """Test ZoomInfo Contact Search endpoint."""

    @pytest.mark.asyncio
    async def test_search_executives_by_domain(self):
        """Searches C-suite contacts at a company."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {
                    "firstName": "Jane",
                    "lastName": "Doe",
                    "jobTitle": "Chief Technology Officer",
                    "email": "jane.doe@acme.com",
                    "phone": "+1-555-0100",
                    "linkedInUrl": "linkedin.com/in/janedoe"
                }
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_contacts(
                domain="acme.com",
                job_titles=["CEO", "CTO", "CFO"]
            )
            assert result["success"] is True
            assert len(result["people"]) >= 1
            assert result["people"][0]["name"] == "Jane Doe"

    @pytest.mark.asyncio
    async def test_contact_search_normalizes_to_people_format(self):
        """Contact data normalizes to match Apollo/PDL people format."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{
                "firstName": "John",
                "lastName": "Smith",
                "jobTitle": "CEO",
                "email": "john@acme.com",
                "phone": "+1-555-0100",
                "linkedInUrl": "linkedin.com/in/johnsmith"
            }]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_contacts(domain="acme.com")
            person = result["people"][0]
            assert "name" in person
            assert "title" in person
            assert "email" in person
            assert "phone" in person
            assert "linkedin" in person

    @pytest.mark.asyncio
    async def test_contact_search_empty_results(self):
        """Returns empty people list when no contacts found."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value={"data": []}):
            result = await client.search_contacts(domain="unknown.com")
            assert result["success"] is True
            assert result["people"] == []


class TestIntentEnrich:
    """Test ZoomInfo Intent Enrich endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_intent_signals(self):
        """Fetches intent signals for a company."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"topic": "Cloud Migration", "score": 85, "audienceStrength": "high"},
                {"topic": "Data Security", "score": 72, "audienceStrength": "medium"}
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_intent(domain="acme.com")
            assert result["success"] is True
            assert len(result["intent_signals"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_intent_empty(self):
        """Returns empty list when no intent data."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value={"data": []}):
            result = await client.enrich_intent(domain="unknown.com")
            assert result["success"] is True
            assert result["intent_signals"] == []


class TestScoopsSearch:
    """Test ZoomInfo Scoops Search endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_scoops(self):
        """Fetches company scoops (business events)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"scoopType": "New Hire", "description": "New CTO appointed",
                 "publishedDate": "2026-01-15"}
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_scoops(domain="acme.com")
            assert result["success"] is True
            assert len(result["scoops"]) >= 1


class TestNewsSearch:
    """Test ZoomInfo News Search endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_news(self):
        """Fetches company news articles."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"title": "Acme raises Series B", "url": "https://example.com/news"}
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_news(company_name="Acme Corp")
            assert result["success"] is True
            assert len(result["articles"]) >= 1


class TestTechEnrich:
    """Test ZoomInfo Technology Enrichment endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_technologies(self):
        """Fetches installed technologies for a company."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"technologyName": "Salesforce", "category": "CRM"},
                {"technologyName": "AWS", "category": "Cloud Infrastructure"}
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_technologies(domain="acme.com")
            assert result["success"] is True
            assert len(result["technologies"]) == 2


class TestErrorHandling:
    """Test error handling patterns."""

    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self):
        """Returns failure with auth error on 401."""
        import httpx
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="invalid-token")
        mock_request = MagicMock()
        mock_response = MagicMock(status_code=401)
        with patch.object(
            client, "_make_request", new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=mock_request, response=mock_response
            )
        ):
            result = await client.enrich_company(domain="acme.com")
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """Returns failure on timeout."""
        import httpx
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          side_effect=httpx.TimeoutException("Timeout")):
            result = await client.enrich_company(domain="acme.com")
            assert result["success"] is False
            assert "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_handles_network_error(self):
        """Returns failure on network error."""
        import httpx
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          side_effect=httpx.ConnectError("Connection refused")):
            result = await client.enrich_company(domain="acme.com")
            assert result["success"] is False
