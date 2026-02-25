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


class TestContactSearchPayloadFormat:
    """Verify the Contact Search payload sends managementLevel as an array."""

    @pytest.mark.asyncio
    async def test_management_level_sent_as_array_not_string(self):
        """managementLevel must be a list ['C-Level'], not a string 'C-Level'.
        ZoomInfo silently returns 0 results when passed as a string."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture_payload(endpoint, payload):
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

        async def capture_payload(endpoint, payload):
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

        async def capture_payload(endpoint, payload):
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
        """No search payload should include outputFields — it causes HTTP 400."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload):
            captured_payloads.append(payload)
            return {"data": []}

        with patch.object(client, "_make_request", side_effect=capture):
            await client.search_contacts(domain="example.com")

        payloads_with_output = [
            p for p in captured_payloads
            if p.get("data", {}).get("attributes", {}).get("outputFields") is not None
        ]
        assert not payloads_with_output, (
            "search_contacts must NOT include outputFields — it causes HTTP 400 on ZoomInfo GTM. "
            "Found it in payloads: " + str([list(p.get("data", {}).get("attributes", {}).keys()) for p in payloads_with_output])
        )

    @pytest.mark.asyncio
    async def test_search_payload_uses_rpp_not_pagesize(self):
        """Search payloads must use 'rpp' for page size, not 'pageSize'."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def capture(endpoint, payload):
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

        async def capture(endpoint, payload):
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

        async def capture(endpoint, payload):
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

        async def capture(endpoint, payload):
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

        async def capture(endpoint, payload):
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

        async def capture(endpoint, payload):
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

        async def always_return_same(endpoint, payload):
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

        async def capture_endpoint(endpoint, payload):
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
