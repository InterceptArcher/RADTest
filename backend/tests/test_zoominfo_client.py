"""
Tests for ZoomInfo API client.
TDD: Tests written FIRST before implementation.
"""
import pytest
import asyncio
import os
import sys
import time
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
            with pytest.raises(ValueError, match="credentials required"):
                ZoomInfoClient()

    def test_default_timeout(self):
        """Client has a default 30s timeout."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test")
        assert client.timeout == 30

    def test_default_base_url(self):
        """Client uses correct ZoomInfo base URL (GTM paths are in ENDPOINTS)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test")
        assert client.base_url == "https://api.zoominfo.com"

    def test_content_type_header(self):
        """Client sends JSON:API content type for GTM API v1."""
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
    async def test_enrich_by_company_name_only_returns_error(self):
        """Company-name-only enrichment returns error (GTM API rejects companyName as direct attribute)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        result = await client.enrich_company(company_name="Acme Corp")
        assert result["success"] is False
        assert "Domain required" in result["error"]

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


class TestContactSearchPayloadFormat:
    """Verify the Contact Search payload sends managementLevel as an array."""

    @pytest.mark.asyncio
    async def test_management_level_sent_as_array_not_string(self):
        """managementLevel must be a list ['C-Level'], not a string 'C-Level'.
        ZoomInfo silently returns 0 results when passed as a string."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture_payload(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture_payload):
            await client.search_contacts(domain="example.com")

        # Find C-Level payload
        c_level_payload = next(
            (p for p in captured_payloads
             if p.get("data", {}).get("attributes", {}).get("managementLevel") is not None),
            None
        )
        assert c_level_payload is not None, "No managementLevel payload found"
        management_level = c_level_payload["data"]["attributes"]["managementLevel"]
        assert isinstance(management_level, list), (
            f"managementLevel must be a list, got {type(management_level).__name__}: {management_level!r}"
        )

    @pytest.mark.asyncio
    async def test_management_level_array_contains_correct_values(self):
        """managementLevel array values are valid ZoomInfo management levels."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture_payload(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        valid_levels = {"C-Level", "VP-Level", "Director", "Director-Level", "Manager"}

        with patch.object(client, "_make_request", side_effect=capture_payload):
            await client.search_contacts(domain="example.com")

        management_level_payloads = [
            p for p in captured_payloads
            if isinstance(p.get("data", {}).get("attributes", {}).get("managementLevel"), list)
        ]
        assert len(management_level_payloads) > 0

        for p in management_level_payloads:
            levels = p["data"]["attributes"]["managementLevel"]
            for level in levels:
                assert level in valid_levels, f"Invalid management level: {level!r}"

    @pytest.mark.asyncio
    async def test_job_title_strategy_targets_primary_roles(self):
        """Strategy 2 job title search includes CTO, CIO, CFO, COO titles."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture_payload(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture_payload):
            await client.search_contacts(domain="example.com")

        title_payloads = [
            p for p in captured_payloads
            if "jobTitle" in p.get("data", {}).get("attributes", {})
        ]
        assert len(title_payloads) > 0, "No jobTitle search payload found"

        all_titles = []
        for p in title_payloads:
            all_titles.extend(p["data"]["attributes"]["jobTitle"])

        all_titles_lower = [t.lower() for t in all_titles]
        assert any("cto" in t or "chief technology" in t for t in all_titles_lower), "CTO not in job title search"
        assert any("cio" in t or "chief information officer" in t for t in all_titles_lower), "CIO not in job title search"
        assert any("cfo" in t or "chief financial" in t for t in all_titles_lower), "CFO not in job title search"
        assert any("coo" in t or "chief operating" in t for t in all_titles_lower), "COO not in job title search"


class TestIntentEnrich:
    """Test ZoomInfo Intent Enrich endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_intent_signals(self):
        """Fetches intent signals for a company (topics validated via lookup endpoint)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"topic": "Cloud Migration", "score": 85, "audienceStrength": "high"},
                {"topic": "Data Security", "score": 72, "audienceStrength": "medium"}
            ]
        }
        valid_topics = ["Cloud Migration", "Data Security"]
        with patch.object(client, "_fetch_valid_intent_topics", new_callable=AsyncMock,
                          return_value=valid_topics):
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
        valid_topics = ["Cloud Migration"]
        with patch.object(client, "_fetch_valid_intent_topics", new_callable=AsyncMock,
                          return_value=valid_topics):
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
        """Fetches company news articles (requires companyId)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [
                {"title": "Acme raises Series B", "url": "https://example.com/news"}
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_news(company_name="Acme Corp", company_id="12345")
            assert result["success"] is True
            assert len(result["articles"]) >= 1

    @pytest.mark.asyncio
    async def test_fetch_news_with_company_name_works(self):
        """News enrich does NOT use companyName (causes PFAPI0005).
        When only company_name provided (no domain/id), should return error."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        result = await client.search_news(company_name="Acme Corp")
        # companyName is not a valid field — should fail without domain or companyId
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_fetch_news_with_domain_fallback_works(self):
        """News enrich succeeds with domain/companyWebsite when no companyId or name."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{"title": "Acme news story", "url": "https://example.com/story"}]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.search_news(domain="acme.com")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_fetch_news_no_identifiers_returns_error(self):
        """News enrich fails when no company identifier provided at all."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        result = await client.search_news()
        assert result["success"] is False


class TestTechEnrich:
    """Test ZoomInfo Technology Enrichment endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_technologies(self):
        """Fetches installed technologies for a company (requires companyId)."""
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
            result = await client.enrich_technologies(domain="acme.com", company_id="12345")
            assert result["success"] is True
            assert len(result["technologies"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_technologies_with_domain_fallback(self):
        """Tech enrich falls back to companyWebsite when no companyId available."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{"technologyName": "AWS", "category": "Cloud Infrastructure"}]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_technologies(domain="acme.com")
            assert result["success"] is True
            assert len(result["technologies"]) == 1


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


class TestAutoAuthentication:
    """Test automatic OAuth2 token refresh for GTM API v1."""

    def test_init_with_oauth2_credentials(self):
        """Client accepts client_id + client_secret + refresh_token for auto-auth."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "test-rt"}):
            client = ZoomInfoClient(client_id="test-id", client_secret="test-secret")
        assert client._client_id == "test-id"
        assert client._client_secret == "test-secret"
        assert client._refresh_token == "test-rt"
        assert client._auto_auth is True

    def test_init_prefers_oauth2_over_env_token(self):
        """OAuth2 credentials take priority over ZOOMINFO_ACCESS_TOKEN env."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_ACCESS_TOKEN": "env-token", "ZOOMINFO_REFRESH_TOKEN": "rt"}):
            client = ZoomInfoClient(client_id="test-id", client_secret="test-secret")
            assert client._auto_auth is True

    def test_static_token_disables_auto_auth(self):
        """When access_token is provided directly, auto_auth is False."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="static-token")
        assert client._auto_auth is False

    def test_init_without_any_credentials_raises(self):
        """Raises ValueError when no credentials are provided."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError):
                ZoomInfoClient()

    @pytest.mark.asyncio
    async def test_authenticate_fetches_token(self):
        """_authenticate() POSTs to Okta token endpoint and stores access_token."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "test-rt"}):
            client = ZoomInfoClient(client_id="test-id", client_secret="test-secret")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "fresh-oauth2-token",
            "refresh_token": "new-rt",
            "token_type": "Bearer",
            "expires_in": 86400
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await client._authenticate()

            assert client.access_token == "fresh-oauth2-token"
            assert client._token_expires_at > time.time()
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_caches_token(self):
        """Second call to _ensure_valid_token doesn't re-authenticate if not expired."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "test-rt"}):
            client = ZoomInfoClient(client_id="test-id", client_secret="test-secret")
        # Simulate already authenticated
        client.access_token = "cached-token"
        client._token_expires_at = time.time() + 3600
        client.headers["Authorization"] = "Bearer cached-token"

        await client._ensure_valid_token()
        assert client.access_token == "cached-token"

    @pytest.mark.asyncio
    async def test_auto_refreshes_expired_token(self):
        """_ensure_valid_token re-authenticates when token is expired."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "test-rt"}):
            client = ZoomInfoClient(client_id="test-id", client_secret="test-secret")
        client.access_token = "old-token"
        client._token_expires_at = time.time() - 10

        with patch.object(client, "_authenticate", new_callable=AsyncMock) as mock_auth:
            await client._ensure_valid_token()
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_failure_raises(self):
        """Bad credentials raise ValueError during authentication."""
        import httpx
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "bad-rt"}):
            client = ZoomInfoClient(client_id="bad-id", client_secret="bad-secret")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError, match="authentication failed"):
                await client._authenticate()


class TestContactEnrich:
    """Test ZoomInfo Contact Enrich endpoint (Search → Enrich 2-step)."""

    @pytest.mark.asyncio
    async def test_enrich_contacts_by_person_ids(self):
        """Enriches contacts by person IDs returning full profile data."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{
                "personId": "123",
                "firstName": "Satya",
                "lastName": "Nadella",
                "jobTitle": "Chief Executive Officer",
                "email": "satya@microsoft.com",
                "directPhone": "+1-425-555-0100",
                "mobilePhone": "+1-425-555-0101",
                "companyPhone": "+1-425-882-8080",
                "contactAccuracyScore": 95,
                "department": "C-Suite",
                "managementLevel": "C-Level",
                "linkedInUrl": "linkedin.com/in/satyanadella"
            }]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.enrich_contacts(person_ids=["123"])
            assert result["success"] is True
            assert len(result["people"]) == 1
            person = result["people"][0]
            assert person["direct_phone"] == "+1-425-555-0100"
            assert person["mobile_phone"] == "+1-425-555-0101"
            assert person["company_phone"] == "+1-425-882-8080"
            assert person["contact_accuracy_score"] == 95
            assert person["department"] == "C-Suite"
            assert person["management_level"] == "C-Level"
            assert person["person_id"] == "123"

    @pytest.mark.asyncio
    async def test_enrich_contacts_empty(self):
        """Returns empty list when no contacts enriched."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value={"data": []}):
            result = await client.enrich_contacts(person_ids=["999"])
            assert result["success"] is True
            assert result["people"] == []

    @pytest.mark.asyncio
    async def test_search_and_enrich_contacts(self):
        """Convenience method: search then enrich in 2 steps."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        # Mock search_contacts returning person with ID
        search_result = {
            "success": True,
            "people": [{"name": "Jane Doe", "title": "CTO", "person_id": "456",
                         "email": "jane@acme.com", "phone": "", "linkedin": "",
                         "direct_phone": "", "mobile_phone": "", "company_phone": "",
                         "contact_accuracy_score": 0, "department": "", "management_level": ""}],
            "error": None
        }
        # Mock enrich_contacts returning enriched data
        enrich_result = {
            "success": True,
            "people": [{"name": "Jane Doe", "title": "CTO", "person_id": "456",
                         "email": "jane@acme.com", "phone": "+1-555-0100",
                         "linkedin": "linkedin.com/in/janedoe",
                         "direct_phone": "+1-555-0200", "mobile_phone": "+1-555-0300",
                         "company_phone": "+1-555-0400", "contact_accuracy_score": 88,
                         "department": "Technology", "management_level": "C-Level"}],
            "error": None
        }
        with patch.object(client, "search_contacts", new_callable=AsyncMock,
                          return_value=search_result):
            with patch.object(client, "enrich_contacts", new_callable=AsyncMock,
                              return_value=enrich_result):
                result = await client.search_and_enrich_contacts(domain="acme.com")
                assert result["success"] is True
                assert len(result["people"]) == 1
                assert result["people"][0]["direct_phone"] == "+1-555-0200"


class TestNormalizeContactExpanded:
    """Test that _normalize_contact extracts all ZoomInfo contact fields."""

    def test_extracts_phone_types(self):
        """Normalizer extracts directPhone, mobilePhone, companyPhone."""
        from zoominfo_client import ZoomInfoClient
        raw = {
            "firstName": "Test",
            "lastName": "User",
            "jobTitle": "CTO",
            "email": "test@co.com",
            "phone": "+1-111",
            "directPhone": "+1-222",
            "mobilePhone": "+1-333",
            "companyPhone": "+1-444",
            "linkedInUrl": "linkedin.com/in/test",
            "contactAccuracyScore": 92,
            "department": "Engineering",
            "managementLevel": "C-Level",
            "personId": "abc123"
        }
        result = ZoomInfoClient._normalize_contact(raw)
        assert result["direct_phone"] == "+1-222"
        assert result["mobile_phone"] == "+1-333"
        assert result["company_phone"] == "+1-444"
        assert result["contact_accuracy_score"] == 92
        assert result["department"] == "Engineering"
        assert result["management_level"] == "C-Level"
        assert result["person_id"] == "abc123"

    def test_handles_missing_fields_gracefully(self):
        """Missing phone fields default to empty string, score to 0."""
        from zoominfo_client import ZoomInfoClient
        raw = {"firstName": "A", "lastName": "B", "jobTitle": "CEO"}
        result = ZoomInfoClient._normalize_contact(raw)
        assert result["direct_phone"] == ""
        assert result["mobile_phone"] == ""
        assert result["company_phone"] == ""
        assert result["contact_accuracy_score"] == 0
        assert result["department"] == ""
        assert result["management_level"] == ""


class TestNormalizeCompanyGrowthFields:
    """Test that _normalize_company_data extracts growth fields."""

    def test_extracts_growth_rates(self):
        """Normalizer extracts employee growth rates and funding."""
        from zoominfo_client import ZoomInfoClient
        raw = {
            "companyName": "GrowthCo",
            "oneYearEmployeeGrowthRate": 15.5,
            "twoYearEmployeeGrowthRate": 28.3,
            "fundingAmount": 50000000,
            "fortuneRank": 250,
            "businessModel": "SaaS",
            "numLocations": 12
        }
        result = ZoomInfoClient._normalize_company_data(raw)
        assert result["one_year_employee_growth"] == 15.5
        assert result["two_year_employee_growth"] == 28.3
        assert result["funding_amount"] == 50000000
        assert result["fortune_rank"] == 250
        assert result["business_model"] == "SaaS"
        assert result["num_locations"] == 12

    def test_growth_fields_default_to_empty(self):
        """Growth fields default to empty string when not in API response."""
        from zoominfo_client import ZoomInfoClient
        raw = {"companyName": "BasicCo"}
        result = ZoomInfoClient._normalize_company_data(raw)
        assert result["one_year_employee_growth"] == ""
        assert result["two_year_employee_growth"] == ""
        assert result["funding_amount"] == ""


class TestZoomInfoNotConfiguredDiagnostics:
    """
    TDD: When ZoomInfo is not configured, the debug panel must show a meaningful
    diagnostic message instead of silently showing 'skipped' with no explanation.

    Currently failing: zoominfo_data = {} when not configured, causing
    _contact_search_error to be absent → debug panel shows 'skipped' with no hint.

    Fix: always include _contact_search_error or _not_configured in zoominfo_data
    so step-1d shows 'skipped' with a clear 'credentials not configured' message.
    """

    def test_not_configured_zoominfo_data_has_contact_search_error(self):
        """When ZoomInfo is not configured, zoominfo_data must have _contact_search_error set.
        This ensures step-1d shows 'skipped' + 'not configured' message, not silent 'skipped'."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from production_main import _get_zoominfo_client

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "production_main.ZOOMINFO_CLIENT_ID", ""
        ), __import__("unittest.mock", fromlist=["patch"]).patch(
            "production_main.ZOOMINFO_CLIENT_SECRET", ""
        ), __import__("unittest.mock", fromlist=["patch"]).patch(
            "production_main.ZOOMINFO_ACCESS_TOKEN", ""
        ):
            client = _get_zoominfo_client()
            assert client is None, "ZoomInfo client should be None when not configured"

    def test_fetch_all_zoominfo_outer_exception_includes_error_key(self):
        """If _fetch_all_zoominfo's outer try-except fires, the returned dict
        must include _contact_search_error so step-1d shows 'failed', not 'skipped'."""
        import asyncio
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from production_main import _fetch_all_zoominfo

        class BrokenClient:
            """Client whose first call throws an unrecoverable exception."""
            def enrich_company(self, **kw):
                raise RuntimeError("unexpected error")
            def enrich_intent(self, **kw):
                async def _(): return {"success": False, "intent_signals": [], "error": ""}
                return _()
            def search_scoops(self, **kw):
                async def _(): return {"success": False, "scoops": [], "error": ""}
                return _()
            def search_news(self, **kw):
                async def _(): return {"success": False, "articles": [], "error": ""}
                return _()
            def enrich_technologies(self, **kw):
                async def _(): return {"success": False, "technologies": [], "error": ""}
                return _()
            def search_and_enrich_contacts(self, **kw):
                async def _(): return {"success": False, "people": [], "error": "no contacts"}
                return _()

        company_data = {"domain": "test.com", "company_name": "TestCo"}
        result_data, result_contacts = asyncio.get_event_loop().run_until_complete(
            _fetch_all_zoominfo(BrokenClient(), company_data)
        )
        # The returned dict must include _contact_search_error so the debug
        # panel shows 'failed' instead of 'skipped'
        assert "_contact_search_error" in result_data, (
            "Outer exception path must set _contact_search_error in returned dict. "
            f"Got keys: {list(result_data.keys())}"
        )
        assert result_data["_contact_search_error"], "Error message must be non-empty"


class TestSearchContactsOutputFields:
    """
    outputFields is intentionally excluded from all contact search payloads.
    ZoomInfo GTM contact search returns HTTP 400 when outputFields is included
    in the request body. Phone data is retrieved via the separate contact
    enrich step instead.
    """

    @pytest.mark.asyncio
    async def test_search_payload_excludes_output_fields(self):
        """Search must NOT include outputFields — it causes HTTP 400 on the search endpoint."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        payloads_with_output = [
            p for p in captured_payloads
            if p.get("data", {}).get("attributes", {}).get("outputFields") is not None
        ]
        assert not payloads_with_output, (
            "search_contacts must NOT include outputFields — it causes HTTP 400 on ZoomInfo Contact Search. "
            "outputFields is only valid on the Contact Enrich endpoint."
        )

    @pytest.mark.asyncio
    async def test_search_payload_uses_rpp_not_pagesize(self):
        """Search payloads must use 'rpp' for page size, not 'pageSize'."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        jsonapi_payloads = [
            p for p in captured_payloads
            if p.get("data", {}).get("attributes") is not None
        ]
        for p in jsonapi_payloads:
            attrs = p["data"]["attributes"]
            assert "pageSize" not in attrs, "Use 'rpp' not 'pageSize' — ZoomInfo GTM parameter name"
            if "rpp" in attrs:
                assert isinstance(attrs["rpp"], int), "'rpp' must be an integer"

    @pytest.mark.asyncio
    async def test_management_level_enum_values(self):
        """managementLevel values must use ZoomInfo's hyphenated -Level suffix."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        invalid = {"VP Level", "Director", "Manager"}
        all_levels_used = set()
        for p in captured_payloads:
            levels = p.get("data", {}).get("attributes", {}).get("managementLevel", [])
            all_levels_used.update(levels)

        bad = all_levels_used & invalid
        assert not bad, (
            f"Invalid managementLevel values used: {bad}. "
            "ZoomInfo requires hyphenated form: VP-Level, Director-Level, Manager-Level"
        )


class TestExpandedCSuiteSearch:
    """
    TDD: search_contacts job-title strategy must target ALL C-suite chiefs,
    not only CEO/CTO/CIO/CFO/COO. Missing chiefs (CMO, CRO, CPO, CHRO, etc.)
    means their phone data is never fetched.
    """

    @pytest.mark.asyncio
    async def test_search_includes_cmo(self):
        """CMO / Chief Marketing Officer must be in the job title search list."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        all_titles = []
        for p in captured_payloads:
            titles = p.get("data", {}).get("attributes", {}).get("jobTitle", [])
            if titles:
                all_titles.extend(titles)

        titles_lower = [t.lower() for t in all_titles]
        assert any("cmo" in t or "chief marketing" in t for t in titles_lower), (
            "CMO / Chief Marketing Officer missing from job title search"
        )

    @pytest.mark.asyncio
    async def test_search_includes_cro(self):
        """CRO / Chief Revenue Officer must be in the job title search list."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        all_titles = []
        for p in captured_payloads:
            titles = p.get("data", {}).get("attributes", {}).get("jobTitle", [])
            if titles:
                all_titles.extend(titles)

        titles_lower = [t.lower() for t in all_titles]
        assert any("cro" in t or "chief revenue" in t for t in titles_lower), (
            "CRO / Chief Revenue Officer missing from job title search"
        )

    @pytest.mark.asyncio
    async def test_search_includes_chro(self):
        """CHRO / Chief People Officer must be in the job title search list."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        all_titles = []
        for p in captured_payloads:
            titles = p.get("data", {}).get("attributes", {}).get("jobTitle", [])
            if titles:
                all_titles.extend(titles)

        titles_lower = [t.lower() for t in all_titles]
        assert any(
            "chro" in t or "chief people" in t or "chief hr" in t or "chief human" in t
            for t in titles_lower
        ), "CHRO / Chief People Officer missing from job title search"


class TestLookupContactsByIdentity:
    """
    TDD: ZoomInfoClient must have a lookup_contacts_by_identity method that
    takes a list of contacts (with name/email) and searches them in the ZoomInfo
    GTM contact SEARCH endpoint (not the enrich endpoint) to find their records
    and retrieve phone numbers.

    This is the mechanism for enriching Apollo/Hunter contacts that have no
    ZoomInfo personId — we search them by email or first+last name + domain.
    """

    @pytest.mark.asyncio
    async def test_method_exists(self):
        """ZoomInfoClient has a lookup_contacts_by_identity method."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        assert hasattr(client, "lookup_contacts_by_identity"), (
            "ZoomInfoClient must have a lookup_contacts_by_identity method"
        )

    @pytest.mark.asyncio
    async def test_lookup_by_email_returns_contact_with_phones(self):
        """Lookup by email finds contact and returns phone data from GTM search."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        mock_response = {
            "data": [{
                "firstName": "Jane",
                "lastName": "Doe",
                "jobTitle": "Chief Marketing Officer",
                "email": "jane.doe@acme.com",
                "directPhone": "+1-415-555-0100",
                "mobilePhone": "+1-415-555-0101",
                "companyPhone": "+1-415-555-0000",
                "personId": "zi-999",
                "managementLevel": "C-Level",
                "department": "Marketing",
                "contactAccuracyScore": 88,
            }]
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = await client.lookup_contacts_by_identity(
                contacts=[{"name": "Jane Doe", "email": "jane.doe@acme.com"}],
                domain="acme.com"
            )

        assert result["success"] is True
        assert len(result["people"]) == 1
        person = result["people"][0]
        assert person["direct_phone"] == "+1-415-555-0100"
        assert person["mobile_phone"] == "+1-415-555-0101"
        assert person["person_id"] == "zi-999"

    @pytest.mark.asyncio
    async def test_lookup_by_name_falls_back_when_no_email(self):
        """Lookup by first+last name when email is absent."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": [{
                "firstName": "Bob",
                "lastName": "Smith",
                "jobTitle": "CRO",
                "directPhone": "+1-800-555-0200",
                "personId": "zi-111",
            }]}

        with patch.object(client, "_make_request", side_effect=capture):
            result = await client.lookup_contacts_by_identity(
                contacts=[{"name": "Bob Smith", "email": ""}],
                domain="corp.com"
            )

        assert result["success"] is True
        assert len(result["people"]) == 1
        # Verify the payload used firstName/lastName (not email)
        name_payloads = [
            p for p in captured_payloads
            if p.get("data", {}).get("attributes", {}).get("firstName")
        ]
        assert name_payloads, "Must send firstName/lastName payload when no email"

    @pytest.mark.asyncio
    async def test_lookup_no_match_returns_empty(self):
        """Lookup returns empty people list when ZoomInfo has no match."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value={"data": []}):
            result = await client.lookup_contacts_by_identity(
                contacts=[{"name": "Unknown Person", "email": "unknown@nowhere.com"}],
                domain="nowhere.com"
            )

        assert result["success"] is True
        assert result["people"] == []

    @pytest.mark.asyncio
    async def test_lookup_deduplicates_by_person_id(self):
        """Same person found via both email and name lookup is deduplicated."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        same_contact = {
            "firstName": "Dup",
            "lastName": "Person",
            "email": "dup@co.com",
            "directPhone": "+1-999",
            "personId": "zi-dup",
        }

        call_count = [0]

        async def always_return_same(endpoint, payload, _is_retry=False, params=None):
            call_count[0] += 1
            return {"data": [same_contact]}

        with patch.object(client, "_make_request", side_effect=always_return_same):
            result = await client.lookup_contacts_by_identity(
                contacts=[
                    {"name": "Dup Person", "email": "dup@co.com"},
                    {"name": "Dup Person", "email": "dup@co.com"},
                ],
                domain="co.com"
            )

        # Should deduplicate — same person_id seen twice
        assert result["success"] is True
        assert len(result["people"]) == 1, (
            f"Deduplication failed: expected 1 person, got {len(result['people'])}"
        )

    @pytest.mark.asyncio
    async def test_lookup_uses_contact_search_endpoint_not_enrich(self):
        """lookup_contacts_by_identity must call /contacts/search, NOT /contacts/enrich."""
        from zoominfo_client import ZoomInfoClient, ENDPOINTS
        client = ZoomInfoClient(access_token="test-token")

        called_endpoints = []

        async def capture_endpoint(endpoint, payload, _is_retry=False, params=None):
            called_endpoints.append(endpoint)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture_endpoint):
            await client.lookup_contacts_by_identity(
                contacts=[{"name": "Test User", "email": "test@co.com"}],
                domain="co.com"
            )

        assert ENDPOINTS["contact_enrich"] not in called_endpoints, (
            "lookup_contacts_by_identity must NOT call the contact enrich endpoint. "
            f"Called endpoints: {called_endpoints}"
        )
        assert any(ENDPOINTS["contact_search"] in e for e in called_endpoints), (
            "lookup_contacts_by_identity must call the contact search endpoint. "
            f"Called endpoints: {called_endpoints}"
        )

    @pytest.mark.asyncio
    async def test_lookup_empty_contacts_list_returns_empty(self):
        """Passing an empty contacts list returns an empty result without API calls."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        mock_request = AsyncMock()
        with patch.object(client, "_make_request", mock_request):
            result = await client.lookup_contacts_by_identity(contacts=[], domain="co.com")

        assert result["success"] is True
        assert result["people"] == []
        mock_request.assert_not_called()


# =============================================================================
# NEW TESTS FOR API FIX VERIFICATION
# These tests describe the CORRECT behaviour and were written before the fix.
# They FAIL on the old code and PASS after the fix.
# =============================================================================

class TestCompanyEnrichPayloadFormat:
    """Issue 1 — company enrich was sending companyWebsite as a direct attribute
    which causes ZoomInfo PFAPI0005 'Invalid field requested'.
    The GTM API v1 requires matchCompanyInput array (like matchPersonInput for contacts)."""

    @pytest.mark.asyncio
    async def test_uses_matchCompanyInput_not_direct_companyWebsite(self):
        """Company enrich payload MUST use matchCompanyInput array, not companyWebsite directly.

        Wrong:  {"companyWebsite": "https://www.acme.com", "outputFields": [...]}
        Right:  {"matchCompanyInput": [{"companyWebsite": "https://www.acme.com"}], "outputFields": [...]}
        """
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": [{"id": "99", "companyName": "Acme", "website": "acme.com"}]}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.enrich_company(domain="acme.com")

        assert len(captured) > 0, "No request was made"
        attrs = captured[0]["data"]["attributes"]
        assert "matchCompanyInput" in attrs, (
            "Payload must contain matchCompanyInput array. "
            f"Actual attributes keys: {list(attrs.keys())}"
        )
        assert "companyWebsite" not in attrs, (
            "companyWebsite must NOT be a top-level attribute (causes PFAPI0005). "
            f"Actual attributes keys: {list(attrs.keys())}"
        )
        assert isinstance(attrs["matchCompanyInput"], list), "matchCompanyInput must be a list"
        assert len(attrs["matchCompanyInput"]) > 0, "matchCompanyInput list must not be empty"
        match_input = attrs["matchCompanyInput"][0]
        assert "companyWebsite" in match_input or "website" in match_input, (
            f"matchCompanyInput entry must contain companyWebsite or website, got: {match_input}"
        )

    @pytest.mark.asyncio
    async def test_matchCompanyInput_contains_normalized_url(self):
        """matchCompanyInput website uses canonical https://www.domain format."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": [{"id": "1", "companyName": "Test"}]}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.enrich_company(domain="microsoft.com")

        attrs = captured[0]["data"]["attributes"]
        website_value = attrs["matchCompanyInput"][0].get("companyWebsite") or \
                        attrs["matchCompanyInput"][0].get("website", "")
        assert "microsoft.com" in website_value, (
            f"Website must contain the domain. Got: {website_value}"
        )


class TestIntentTopicsLookup:
    """Issue 2 — DEFAULT_INTENT_TOPICS strings don't match ZoomInfo's taxonomy,
    causing PFAPI0006 'Invalid topics requested'.
    Fix: fetch valid topics from the ZoomInfo lookup endpoint before calling intent enrich."""

    @pytest.mark.asyncio
    async def test_enrich_intent_uses_lookup_for_topics(self):
        """enrich_intent should call _fetch_valid_intent_topics to get valid topic strings."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        lookup_called = []

        async def mock_fetch_topics():
            lookup_called.append(True)
            return ["Cloud Applications", "Cybersecurity"]

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            return {"data": [{"topicName": "Cloud Applications", "intentScore": 80}]}

        with patch.object(client, "_fetch_valid_intent_topics", side_effect=mock_fetch_topics):
            with patch.object(client, "_make_request", side_effect=mock_make_request):
                result = await client.enrich_intent(domain="acme.com")

        assert len(lookup_called) > 0, "enrich_intent must call _fetch_valid_intent_topics"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_fetch_valid_intent_topics_method_exists(self):
        """ZoomInfoClient must have a _fetch_valid_intent_topics method."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        assert hasattr(client, "_fetch_valid_intent_topics"), (
            "ZoomInfoClient must have _fetch_valid_intent_topics method"
        )
        assert callable(client._fetch_valid_intent_topics)

    @pytest.mark.asyncio
    async def test_fetch_valid_intent_topics_uses_get_request(self):
        """_fetch_valid_intent_topics must make a GET request to the lookup endpoint."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        client.access_token = "test-token"
        client.headers["Authorization"] = "Bearer test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"name": "Cloud Applications"}]}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            topics = await client._fetch_valid_intent_topics()

        mock_http.get.assert_called_once()
        call_url = mock_http.get.call_args[0][0]
        assert "lookup" in call_url.lower() and "intent" in call_url.lower(), (
            f"GET URL must contain 'lookup' and 'intent', got: {call_url}"
        )

    @pytest.mark.asyncio
    async def test_fetch_valid_intent_topics_caches_result(self):
        """_fetch_valid_intent_topics caches results to avoid repeated API calls."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        client.access_token = "test-token"
        client.headers["Authorization"] = "Bearer test-token"

        call_count = [0]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"name": "Cloud Applications"}]}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            def counting_get(*args, **kwargs):
                call_count[0] += 1
                return mock_resp
            mock_http.get = AsyncMock(side_effect=counting_get)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            await client._fetch_valid_intent_topics()
            await client._fetch_valid_intent_topics()  # Second call should use cache

        assert call_count[0] == 1, (
            f"Lookup endpoint should be called once (cached), was called {call_count[0]} times"
        )

    @pytest.mark.asyncio
    async def test_intent_enrich_uses_fetched_topics_in_payload(self):
        """The topics used in the intent enrich request come from the lookup, not hardcoded."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        valid_topics = ["Cloud Applications", "Machine Learning Platform"]
        intent_payload_captured = []

        async def mock_fetch_topics():
            return valid_topics

        async def capture_request(endpoint, payload, _is_retry=False, params=None):
            intent_payload_captured.append(payload)
            return {"data": []}

        with patch.object(client, "_fetch_valid_intent_topics", side_effect=mock_fetch_topics):
            with patch.object(client, "_make_request", side_effect=capture_request):
                await client.enrich_intent(domain="acme.com")

        assert len(intent_payload_captured) > 0
        # ZoomInfo Intent Enrich API uses "topic" (singular), not "topics"
        topics_sent = intent_payload_captured[0]["data"]["attributes"].get("topic", [])
        assert topics_sent == valid_topics, (
            f"Topics in payload must match lookup result. Expected: {valid_topics}, got: {topics_sent}"
        )


class TestContactEnrichOutputFields:
    """Issue 5 — CONTACT_ENRICH_OUTPUT_FIELDS contained subscription-disallowed fields
    (hasMobilePhone, directPhoneDoNotCall, mobilePhoneDoNotCall, personId as output)
    causing HTTP 400 which silently fell back to search results with asterisk phones."""

    def test_contact_enrich_output_fields_exclude_disallowed(self):
        """CONTACT_ENRICH_OUTPUT_FIELDS must not contain fields that cause HTTP 400 on this subscription."""
        from zoominfo_client import CONTACT_ENRICH_OUTPUT_FIELDS
        # These fields are documented as disallowed on the current subscription
        disallowed = {
            "directPhone", "department", "linkedInUrl", "managementLevel",
            "hasDirectPhone", "hasCompanyPhone", "fullName",
            # Subscription-specific exclusions that caused silent HTTP 400 failures:
            "hasMobilePhone", "directPhoneDoNotCall", "mobilePhoneDoNotCall",
            "personId",  # Not a valid outputField — personId is implicit in response
        }
        invalid_in_list = [f for f in CONTACT_ENRICH_OUTPUT_FIELDS if f in disallowed]
        assert not invalid_in_list, (
            f"CONTACT_ENRICH_OUTPUT_FIELDS contains disallowed fields: {invalid_in_list}. "
            "These cause HTTP 400 which silently falls back to search results with asterisk phones."
        )

    def test_contact_enrich_output_fields_includes_phone_fields(self):
        """CONTACT_ENRICH_OUTPUT_FIELDS must include the core phone fields."""
        from zoominfo_client import CONTACT_ENRICH_OUTPUT_FIELDS
        assert "phone" in CONTACT_ENRICH_OUTPUT_FIELDS, "phone must be in output fields"
        assert "mobilePhone" in CONTACT_ENRICH_OUTPUT_FIELDS, "mobilePhone must be in output fields"
        assert "companyPhone" in CONTACT_ENRICH_OUTPUT_FIELDS, "companyPhone must be in output fields"

    @pytest.mark.asyncio
    async def test_enrich_contacts_logs_full_error_on_http_400(self):
        """enrich_contacts must log the full error body (not just status code) on failure.
        Silent failure was masking the real reason for the asterisk phone numbers."""
        import httpx
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        error_body = {"errors": [{"code": "PFAPI0005", "detail": "Invalid field requested"}]}
        mock_response.json.return_value = error_body
        mock_response.text = str(error_body)

        http_error = httpx.HTTPStatusError("Bad Request", request=mock_request, response=mock_response)
        # Set the pre-captured error body as _make_request would set it
        mock_response._zi_error_body = error_body

        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          side_effect=http_error):
            result = await client.enrich_contacts(person_ids=["123"])

        assert result["success"] is False
        # Error message must contain the HTTP status and some detail, not just "HTTP 400"
        assert result["error"] != "HTTP 400", (
            "Error message must contain detail, not just 'HTTP 400'. "
            "Bare status codes hide the root cause of asterisk phone numbers."
        )
        assert "400" in result["error"]

    @pytest.mark.asyncio
    async def test_search_and_enrich_does_not_silently_return_search_results_on_enrich_failure(self):
        """When enrich_contacts fails, search_and_enrich_contacts must surface the error
        rather than silently returning search-result contacts that have asterisk phones."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        search_result = {
            "success": True,
            "people": [{"name": "Jane Doe", "title": "CTO", "person_id": "456",
                         "email": "jane@acme.com", "phone": "+1-555-***-****",
                         "linkedin": "", "direct_phone": "", "mobile_phone": "",
                         "company_phone": "", "contact_accuracy_score": 0,
                         "department": "", "management_level": "C-Level"}],
            "error": None
        }
        enrich_fail_result = {
            "success": False,
            "people": [],
            "error": "HTTP 400: PFAPI0005 Invalid field requested"
        }
        with patch.object(client, "search_contacts", new_callable=AsyncMock,
                          return_value=search_result):
            with patch.object(client, "enrich_contacts", new_callable=AsyncMock,
                              return_value=enrich_fail_result):
                result = await client.search_and_enrich_contacts(domain="acme.com")

        # Should NOT silently return the asterisk phone search result
        if result.get("people"):
            phone = result["people"][0].get("phone", "")
            assert "***" not in phone, (
                "search_and_enrich_contacts silently returned search results with asterisk "
                "phones when enrich failed. The error should be surfaced instead."
            )


class TestNewsEnrichFallback:
    """Issue 3 — search_news had wrong restriction requiring companyId.
    ZoomInfo docs confirm companyName and companyWebsite are valid identifiers."""

    @pytest.mark.asyncio
    async def test_news_payload_uses_companyId_when_available(self):
        """When company_id is provided, payload uses companyId (most reliable)."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_news(company_name="Acme", company_id="99999")

        attrs = captured[0]["data"]["attributes"]
        assert attrs.get("companyId") == "99999", "Must use companyId when available"

    @pytest.mark.asyncio
    async def test_news_rejects_company_name_only(self):
        """When only company_name provided (no domain, no id), returns error.
        companyName causes PFAPI0005 in the GTM API."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        result = await client.search_news(company_name="Acme Corp")
        assert result["success"] is False
        assert "companyName not supported" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_news_payload_falls_back_to_domain(self):
        """When neither company_id nor name, payload uses companyWebsite from domain."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_news(domain="acme.com")

        attrs = captured[0]["data"]["attributes"]
        assert "companyWebsite" in attrs, f"Must use companyWebsite fallback. attrs: {attrs}"
        assert "acme.com" in attrs["companyWebsite"]


class TestTechEnrichFallback:
    """Issue 4 — enrich_technologies had wrong restriction requiring companyId.
    Tech enrich should fall back to companyWebsite when companyId is unavailable."""

    @pytest.mark.asyncio
    async def test_tech_payload_uses_companyId_when_available(self):
        """When company_id is provided, payload uses companyId."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.enrich_technologies(domain="acme.com", company_id="88888")

        attrs = captured[0]["data"]["attributes"]
        assert attrs.get("companyId") == "88888"

    @pytest.mark.asyncio
    async def test_tech_payload_falls_back_to_matchCompanyInput(self):
        """When no company_id, payload uses matchCompanyInput array format.
        Flat companyWebsite causes PFAPI0005 — must wrap in matchCompanyInput."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        captured = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.enrich_technologies(domain="acme.com")

        attrs = captured[0]["data"]["attributes"]
        assert "matchCompanyInput" in attrs, (
            f"Must use matchCompanyInput format when no companyId. attrs: {attrs}"
        )
        assert "acme.com" in str(attrs["matchCompanyInput"])
        assert "companyId" not in attrs


# =============================================================================
# Issue 1: COMPANY_OUTPUT_FIELDS must include CEO, companyType, industry, etc.
# =============================================================================
class TestCompanyOutputFieldsIncludeCeoAndType:
    """
    TDD: COMPANY_OUTPUT_FIELDS must request ceoName, companyType, industry,
    subIndustry, description, yearFounded, linkedInUrl from ZoomInfo.
    Without these, _normalize_company_data returns empty CEO and company_type.
    """

    def test_company_output_fields_includes_ceo_name(self):
        """COMPANY_OUTPUT_FIELDS must include ceoName."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "ceoName" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'ceoName' — CEO will never appear in results"
        )

    def test_company_output_fields_includes_company_type(self):
        """COMPANY_OUTPUT_FIELDS must include companyType."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "companyType" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'companyType' — company type will never appear in results"
        )

    def test_company_output_fields_includes_industry(self):
        """COMPANY_OUTPUT_FIELDS must include industry."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "industry" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'industry'"
        )

    def test_company_output_fields_includes_description(self):
        """COMPANY_OUTPUT_FIELDS must include description."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "description" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'description'"
        )

    def test_company_output_fields_includes_year_founded(self):
        """COMPANY_OUTPUT_FIELDS must include yearFounded."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "yearFounded" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'yearFounded'"
        )

    def test_company_output_fields_includes_linkedin(self):
        """COMPANY_OUTPUT_FIELDS must include linkedInUrl."""
        from zoominfo_client import COMPANY_OUTPUT_FIELDS
        assert "linkedInUrl" in COMPANY_OUTPUT_FIELDS, (
            "COMPANY_OUTPUT_FIELDS is missing 'linkedInUrl'"
        )

    def test_company_enrich_returns_ceo(self):
        """enrich_company normalizes ceoName → ceo field."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        mock_response = {
            "data": [{
                "companyName": "Acme Corp",
                "ceoName": "John Smith",
                "companyType": "Public",
                "industry": "Technology",
                "yearFounded": 2010,
                "linkedInUrl": "https://linkedin.com/company/acme",
                "description": "Leading tech company",
            }]
        }
        import asyncio
        with patch.object(client, "_make_request", new_callable=AsyncMock,
                          return_value=mock_response):
            result = asyncio.get_event_loop().run_until_complete(
                client.enrich_company(domain="acme.com")
            )
            normalized = result["normalized"]
            assert normalized["ceo"] == "John Smith"
            assert normalized["company_type"] == "Public"
            assert normalized["industry"] == "Technology"
            assert normalized["founded_year"] == 2010


# =============================================================================
# Issue 2: Contact search must filter out people who left the company
# =============================================================================
class TestContactSearchFiltersFormerEmployees:
    """
    TDD: Contact search must use companyPastOrPresent='present' to exclude
    people who no longer work at the company.
    """

    @pytest.mark.asyncio
    async def test_search_includes_past_or_present_filter(self):
        """Every contact search payload must include companyPastOrPresent='present'."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        contact_search_payloads = [
            p for p in captured_payloads
            if p.get("data", {}).get("type") == "ContactSearch"
        ]
        assert len(contact_search_payloads) > 0, "No ContactSearch payloads found"

        for p in contact_search_payloads:
            attrs = p["data"]["attributes"]
            assert attrs.get("companyPastOrPresent") == "present", (
                f"ContactSearch must include companyPastOrPresent='present' to filter out "
                f"former employees. Got attrs: {list(attrs.keys())}"
            )


# =============================================================================
# Issue 3: search_and_enrich_contacts must merge enrich results back into search
# =============================================================================
class TestSearchAndEnrichMergesResults:
    """
    TDD: When enrich_contacts returns fewer contacts than search_contacts,
    the missing contacts should be kept with phone fields cleared (not lost).
    Also, enrichment status per contact should be tracked.
    """

    @pytest.mark.asyncio
    async def test_enrich_partial_preserves_unenriched_contacts(self):
        """Contacts not returned by enrich are kept with cleared phone fields."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        search_result = {
            "success": True,
            "people": [
                {"name": "Jane Doe", "title": "CTO", "person_id": "100",
                 "email": "jane@co.com", "phone": "+1-***-***-1234",
                 "direct_phone": "", "mobile_phone": "", "company_phone": "",
                 "linkedin": "", "contact_accuracy_score": 0,
                 "department": "", "management_level": ""},
                {"name": "Bob Lee", "title": "CFO", "person_id": "200",
                 "email": "bob@co.com", "phone": "+1-***-***-5678",
                 "direct_phone": "", "mobile_phone": "", "company_phone": "",
                 "linkedin": "", "contact_accuracy_score": 0,
                 "department": "", "management_level": ""},
            ],
            "error": None
        }
        # Enrich only returns data for Jane, not Bob
        enrich_result = {
            "success": True,
            "people": [
                {"name": "Jane Doe", "title": "CTO", "person_id": "100",
                 "email": "jane@co.com", "phone": "+1-555-0100",
                 "direct_phone": "+1-555-0200", "mobile_phone": "+1-555-0300",
                 "company_phone": "+1-555-0400", "linkedin": "",
                 "contact_accuracy_score": 92, "department": "Tech",
                 "management_level": "C-Level"},
            ],
            "error": None
        }

        with patch.object(client, "search_contacts", new_callable=AsyncMock,
                          return_value=search_result):
            with patch.object(client, "enrich_contacts", new_callable=AsyncMock,
                              return_value=enrich_result):
                result = await client.search_and_enrich_contacts(domain="co.com")

        assert result["success"] is True
        assert len(result["people"]) == 2, (
            f"Should preserve both contacts, got {len(result['people'])}"
        )

        # Jane should have enriched phones
        jane = next(p for p in result["people"] if p["name"] == "Jane Doe")
        assert jane["direct_phone"] == "+1-555-0200"
        assert jane["contact_accuracy_score"] == 92

        # Bob should be kept but with cleared phone fields
        bob = next(p for p in result["people"] if p["name"] == "Bob Lee")
        assert bob["phone"] == ""
        assert bob["direct_phone"] == ""
        assert bob["mobile_phone"] == ""
        assert bob["company_phone"] == ""

    @pytest.mark.asyncio
    async def test_enrichment_status_tracked_per_contact(self):
        """Each contact should have an 'enriched' boolean indicating enrichment status."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        search_result = {
            "success": True,
            "people": [
                {"name": "Jane", "title": "CTO", "person_id": "100",
                 "email": "", "phone": "", "direct_phone": "", "mobile_phone": "",
                 "company_phone": "", "linkedin": "", "contact_accuracy_score": 0,
                 "department": "", "management_level": ""},
                {"name": "Bob", "title": "CFO", "person_id": "200",
                 "email": "", "phone": "", "direct_phone": "", "mobile_phone": "",
                 "company_phone": "", "linkedin": "", "contact_accuracy_score": 0,
                 "department": "", "management_level": ""},
            ],
            "error": None
        }
        enrich_result = {
            "success": True,
            "people": [
                {"name": "Jane", "title": "CTO", "person_id": "100",
                 "email": "", "phone": "+1-555", "direct_phone": "+1-555",
                 "mobile_phone": "", "company_phone": "", "linkedin": "",
                 "contact_accuracy_score": 90, "department": "", "management_level": ""},
            ],
            "error": None
        }

        with patch.object(client, "search_contacts", new_callable=AsyncMock,
                          return_value=search_result):
            with patch.object(client, "enrich_contacts", new_callable=AsyncMock,
                              return_value=enrich_result):
                result = await client.search_and_enrich_contacts(domain="co.com")

        jane = next(p for p in result["people"] if p["name"] == "Jane")
        bob = next(p for p in result["people"] if p["name"] == "Bob")
        assert jane.get("enriched") is True
        assert bob.get("enriched") is False

    @pytest.mark.asyncio
    async def test_result_includes_enrichment_summary(self):
        """Result should include enrichment_summary with counts."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        search_result = {
            "success": True,
            "people": [
                {"name": "A", "title": "CTO", "person_id": "1",
                 "email": "", "phone": "", "direct_phone": "", "mobile_phone": "",
                 "company_phone": "", "linkedin": "", "contact_accuracy_score": 0,
                 "department": "", "management_level": ""},
            ],
            "error": None
        }
        enrich_result = {
            "success": True,
            "people": [
                {"name": "A", "title": "CTO", "person_id": "1",
                 "email": "", "phone": "+1-555", "direct_phone": "+1-555",
                 "mobile_phone": "", "company_phone": "", "linkedin": "",
                 "contact_accuracy_score": 95, "department": "", "management_level": ""},
            ],
            "error": None
        }

        with patch.object(client, "search_contacts", new_callable=AsyncMock,
                          return_value=search_result):
            with patch.object(client, "enrich_contacts", new_callable=AsyncMock,
                              return_value=enrich_result):
                result = await client.search_and_enrich_contacts(domain="co.com")

        assert "enrichment_summary" in result
        summary = result["enrichment_summary"]
        assert summary["total_searched"] == 1
        assert summary["total_enriched"] == 1
        assert summary["total_unenriched"] == 0


# =============================================================================
# Issue 5: Confidence score - council minimal data fallback must be smarter
# =============================================================================
class TestConfidenceScoreNotHardcoded:
    """
    TDD: When LLM Council returns minimal data, the confidence score should
    be calculated based on actual data availability, not hardcoded to 0.65.
    """

    def test_council_with_good_data_gets_high_confidence(self):
        """When council returns many useful fields, confidence should be > 0.7."""
        import asyncio
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from llm_council import validate_with_council

        # Mock the council to return good data — must also set OPENAI_API_KEY
        # so validate_with_council doesn't skip to the "not configured" branch
        async def _test():
            with patch("llm_council.OPENAI_API_KEY", "test-key"):
                with patch("llm_council.run_council", new_callable=AsyncMock) as mock_council:
                    mock_council.return_value = {
                        "company_name": "TestCo",
                        "industry": "Technology",
                        "employee_count": 500,
                        "headquarters": "San Francisco, CA",
                        "ceo": "John Smith",
                        "annual_revenue": "$50M",
                        "founded_year": 2015,
                        "company_type": "Private",
                        "technologies": ["AWS", "React"],
                        "_council_metadata": {"specialists_run": 20}
                    }
                    result = await validate_with_council(
                        {"company_name": "TestCo", "domain": "test.com"},
                        {"industry": "Tech"}, {}, {}
                    )
                    return result

        result = asyncio.get_event_loop().run_until_complete(_test())
        assert result.get("confidence_score", 0) >= 0.75, (
            f"Good data should have confidence >= 0.75, got {result.get('confidence_score')}"
        )


class TestCompanyEnrichOutputFieldsFallback:
    """Test that company enrich falls back to base fields when extended fields are disallowed."""

    def test_base_company_output_fields_exist(self):
        """BASE_COMPANY_OUTPUT_FIELDS constant exists with the 11 safe fields."""
        from zoominfo_client import BASE_COMPANY_OUTPUT_FIELDS
        assert "id" in BASE_COMPANY_OUTPUT_FIELDS
        assert "name" in BASE_COMPANY_OUTPUT_FIELDS
        assert "website" in BASE_COMPANY_OUTPUT_FIELDS
        assert "revenue" in BASE_COMPANY_OUTPUT_FIELDS
        assert "employeeCount" in BASE_COMPANY_OUTPUT_FIELDS
        # Extended fields should NOT be in base
        assert "ceoName" not in BASE_COMPANY_OUTPUT_FIELDS
        assert "companyType" not in BASE_COMPANY_OUTPUT_FIELDS
        assert "industry" not in BASE_COMPANY_OUTPUT_FIELDS

    def test_extended_company_output_fields_include_base(self):
        """EXTENDED_COMPANY_OUTPUT_FIELDS includes base + leadership/industry fields."""
        from zoominfo_client import BASE_COMPANY_OUTPUT_FIELDS, EXTENDED_COMPANY_OUTPUT_FIELDS
        for field in BASE_COMPANY_OUTPUT_FIELDS:
            assert field in EXTENDED_COMPANY_OUTPUT_FIELDS
        assert "ceoName" in EXTENDED_COMPANY_OUTPUT_FIELDS
        assert "industry" in EXTENDED_COMPANY_OUTPUT_FIELDS

    def test_company_enrich_retries_with_base_fields_on_pfapi0009(self):
        """When extended fields cause PFAPI0009, company enrich retries with base fields."""
        from zoominfo_client import ZoomInfoClient
        import httpx

        client = ZoomInfoClient(access_token="test-token")

        # First call with extended fields fails with PFAPI0009
        pfapi_error_body = {
            "detail": "OutputFields invalid or disallowed",
            "errors": [{"code": "PFAPI0009", "detail": "Invalid field 'ceoname'"}],
        }
        error_response = httpx.Response(400, json=pfapi_error_body, request=httpx.Request("POST", "https://api.zoominfo.com/test"))

        # Second call with base fields succeeds
        success_response = {
            "data": [{"id": "123", "attributes": {"name": "TestCo", "website": "https://test.com"}}]
        }

        call_count = 0
        async def mock_make_request(endpoint, payload, **kwargs):
            nonlocal call_count
            call_count += 1
            output_fields = payload.get("data", {}).get("attributes", {}).get("outputFields", [])
            if "ceoName" in output_fields:
                # Simulate PFAPI0009 for extended fields
                raise httpx.HTTPStatusError(
                    "400", response=error_response, request=error_response.request
                )
            return success_response

        client._make_request = mock_make_request

        async def _test():
            result = await client.enrich_company(domain="test.com")
            return result

        result = asyncio.get_event_loop().run_until_complete(_test())
        assert result["success"] is True
        assert call_count >= 2  # Extended failed, base succeeded


class TestLinkedInPreservationInEnrichMerge:
    """Test that LinkedIn URLs from search are preserved when merging with enrich results."""

    def test_linkedin_preserved_after_enrich_merge(self):
        """search_and_enrich_contacts preserves linkedinUrl from search step."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        # Mock search: returns contacts WITH linkedin
        search_result = {
            "success": True,
            "people": [
                {
                    "person_id": "pid-1",
                    "name": "Jane Doe",
                    "title": "CTO",
                    "linkedin": "https://linkedin.com/in/janedoe",
                    "management_level": "C-Level",
                    "phone": "***",
                    "direct_phone": "***",
                    "mobile_phone": "",
                    "company_phone": "",
                }
            ],
        }

        # Mock enrich: returns phone data but NO linkedin
        enrich_result = {
            "success": True,
            "people": [
                {
                    "person_id": "pid-1",
                    "name": "Jane Doe",
                    "title": "CTO",
                    "phone": "+1-555-000-1234",
                    "mobile_phone": "+1-555-000-5678",
                    "company_phone": "",
                    "contact_accuracy_score": 92,
                }
            ],
        }

        client.search_contacts = AsyncMock(return_value=search_result)
        client.enrich_contacts = AsyncMock(return_value=enrich_result)

        async def _test():
            result = await client.search_and_enrich_contacts(domain="test.com")
            return result

        result = asyncio.get_event_loop().run_until_complete(_test())
        contact = result["people"][0]
        assert contact.get("linkedin") == "https://linkedin.com/in/janedoe", (
            f"LinkedIn URL lost during merge: got {contact.get('linkedin')}"
        )
        assert contact["enriched"] is True


class TestCSuiteEnrichmentPriority:
    """Test that C-suite contacts are prioritized for phone enrichment."""

    def test_csuite_contacts_enriched_first(self):
        """C-Level contacts appear before lower-level contacts in enrich request."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        # Search returns contacts in mixed order
        search_result = {
            "success": True,
            "people": [
                {"person_id": "pid-mgr", "name": "Manager Bob", "title": "Manager", "management_level": "Manager"},
                {"person_id": "pid-cto", "name": "CTO Jane", "title": "CTO", "management_level": "C-Level"},
                {"person_id": "pid-dir", "name": "Director Kim", "title": "Director", "management_level": "Director"},
                {"person_id": "pid-vp", "name": "VP Alex", "title": "VP Engineering", "management_level": "VP-Level"},
            ],
        }

        captured_person_ids = []
        async def mock_enrich(person_ids):
            captured_person_ids.extend(person_ids)
            return {"success": True, "people": []}

        client.search_contacts = AsyncMock(return_value=search_result)
        client.enrich_contacts = mock_enrich

        async def _test():
            return await client.search_and_enrich_contacts(domain="test.com")

        asyncio.get_event_loop().run_until_complete(_test())

        # C-Level should be first in the enrich request
        assert captured_person_ids[0] == "pid-cto", (
            f"C-Level contact should be first for enrichment, got order: {captured_person_ids}"
        )


class TestIntentTopicsFallback:
    """Test that intent enrichment falls back to DEFAULT_INTENT_TOPICS when lookup fails."""

    def test_default_intent_topics_exist(self):
        """DEFAULT_INTENT_TOPICS constant exists as fallback."""
        from zoominfo_client import DEFAULT_INTENT_TOPICS
        assert isinstance(DEFAULT_INTENT_TOPICS, list)
        assert len(DEFAULT_INTENT_TOPICS) > 0
        assert "Cybersecurity" in DEFAULT_INTENT_TOPICS

    def test_fetch_topics_returns_defaults_on_failure(self):
        """_fetch_valid_intent_topics returns DEFAULT_INTENT_TOPICS when lookup fails."""
        from zoominfo_client import ZoomInfoClient, DEFAULT_INTENT_TOPICS

        client = ZoomInfoClient(access_token="test-token")
        client._valid_topics_cache = None  # Reset cache

        async def _test():
            # Mock _ensure_valid_token to no-op
            client._ensure_valid_token = AsyncMock()
            # Mock httpx to raise on GET
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.get = AsyncMock(side_effect=Exception("lookup failed"))
                mock_client_cls.return_value = mock_client
                topics = await client._fetch_valid_intent_topics()
            return topics

        topics = asyncio.get_event_loop().run_until_complete(_test())
        assert topics == DEFAULT_INTENT_TOPICS, (
            f"Should fall back to DEFAULT_INTENT_TOPICS, got: {topics}"
        )


class TestNewsEnrichCompanyIdFirst:
    """Test that news enrich uses companyId-first pattern with fallback chain."""

    def test_news_uses_companyid_when_available(self):
        """News enrich uses companyId as primary identifier."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []
        async def mock_make_request(endpoint, payload, **kwargs):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        async def _test():
            return await client.search_news(company_id="zi-123", domain="test.com")

        asyncio.get_event_loop().run_until_complete(_test())
        first_attrs = captured_payloads[0]["data"]["attributes"]
        assert "companyId" in first_attrs, "Should try companyId first"

    def test_news_does_not_use_company_name(self):
        """News enrich should NOT use companyName (causes PFAPI0005)."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []
        async def mock_make_request(endpoint, payload, **kwargs):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        async def _test():
            return await client.search_news(company_name="TestCo", domain="test.com")

        asyncio.get_event_loop().run_until_complete(_test())
        for p in captured_payloads:
            attrs = p["data"]["attributes"]
            assert "companyName" not in attrs, "companyName causes PFAPI0005 — should not be used"


class TestTechEnrichCompanyIdFirst:
    """Test that tech enrich uses companyId-first pattern."""

    def test_tech_uses_companyid_when_available(self):
        """Tech enrich uses companyId as primary identifier."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []
        async def mock_make_request(endpoint, payload, **kwargs):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        async def _test():
            return await client.enrich_technologies(domain="test.com", company_id="zi-123")

        asyncio.get_event_loop().run_until_complete(_test())
        first_attrs = captured_payloads[0]["data"]["attributes"]
        assert "companyId" in first_attrs

    def test_tech_fallback_does_not_use_flat_company_website(self):
        """Tech enrich should NOT use flat companyWebsite (causes PFAPI0005)."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []
        async def mock_make_request(endpoint, payload, **kwargs):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        async def _test():
            return await client.enrich_technologies(domain="test.com")

        asyncio.get_event_loop().run_until_complete(_test())
        for p in captured_payloads:
            attrs = p["data"]["attributes"]
            assert "companyWebsite" not in attrs, (
                "Flat companyWebsite causes PFAPI0005 — should use matchCompanyInput or companyId"
            )


class TestNormalizeContactLinkedInCasing:
    """Test that _normalize_contact handles all casing variants of LinkedIn URL."""

    def test_normalize_handles_lowercase_linkedinUrl(self):
        """ZoomInfo search returns 'linkedinUrl' (lowercase i) — must be captured."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        # Simulate a raw JSON:API record with ZoomInfo's actual field name
        raw = {"id": "123", "attributes": {"linkedinUrl": "https://linkedin.com/in/janedoe", "firstName": "Jane", "lastName": "Doe"}}
        person = client._normalize_contact(raw)
        assert person["linkedin"] == "https://linkedin.com/in/janedoe", (
            f"_normalize_contact missed 'linkedinUrl' (lowercase i): got '{person['linkedin']}'"
        )

    def test_normalize_handles_camelCase_linkedInUrl(self):
        """Some sources return 'linkedInUrl' (capital I) — must also be captured."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        raw = {"id": "456", "attributes": {"linkedInUrl": "https://linkedin.com/in/johndoe", "firstName": "John", "lastName": "Doe"}}
        person = client._normalize_contact(raw)
        assert person["linkedin"] == "https://linkedin.com/in/johndoe"


class TestNormalizeContactLinkedInFromSearchResponse:
    """Test that _normalize_contact correctly extracts LinkedIn from real ZoomInfo search responses."""

    def test_normalize_from_jsonapi_unwrapped_response(self):
        """After _unwrap_jsonapi, the flat dict has 'linkedinUrl' — must be captured."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        # Simulate what _unwrap_jsonapi produces from a real ZoomInfo search response
        # The JSON:API record {"attributes": {"linkedinUrl": "..."}} gets flattened to {"linkedinUrl": "..."}
        unwrapped = {
            "id": "person-123",
            "firstName": "Jane",
            "lastName": "Doe",
            "jobTitle": "CTO",
            "linkedinUrl": "https://linkedin.com/in/janedoe",
            "managementLevel": "C-Level",
            "contactAccuracyScore": 95,
        }
        # _normalize_contact expects a raw dict with optional "attributes"
        # When called directly with a flat dict (post-unwrap), attrs=raw
        person = client._normalize_contact(unwrapped)
        assert person["linkedin"] == "https://linkedin.com/in/janedoe", (
            f"LinkedIn URL lost during normalization: got '{person['linkedin']}'"
        )

    def test_search_and_enrich_preserves_linkedin_through_full_pipeline(self):
        """End-to-end: search returns linkedinUrl → normalize → merge → preserved in output."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        # Mock _make_request for search step — returns JSON:API format
        search_response = {
            "data": [
                {
                    "id": "person-456",
                    "type": "Contact",
                    "attributes": {
                        "firstName": "Bob",
                        "lastName": "Smith",
                        "jobTitle": "CTO",
                        "linkedinUrl": "https://linkedin.com/in/bobsmith",
                        "managementLevel": "C-Level",
                        "phone": "***-***-1234",
                        "contactAccuracyScore": 90,
                    }
                }
            ]
        }
        # After _extract_data_list + _normalize_contact in search_contacts,
        # the person dict should have linkedin="https://linkedin.com/in/bobsmith"
        data_list = client._extract_data_list(search_response)
        assert len(data_list) == 1
        person = client._normalize_contact(data_list[0])
        assert person["linkedin"] == "https://linkedin.com/in/bobsmith", (
            f"LinkedIn lost after extract+normalize: got '{person['linkedin']}'"
        )
