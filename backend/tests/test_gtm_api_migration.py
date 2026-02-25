"""
Tests for ZoomInfo GTM API v1 migration.
TDD: Tests written FIRST — validates endpoint paths, JSON:API request format,
content-type headers, phone field output configuration, and OAuth2 auth flow.

These tests MUST FAIL against the old legacy endpoint code and PASS after migration.
"""
import pytest
import os
import sys
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

# Add worker directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker"))


class TestGTMEndpointPaths:
    """Validate all endpoints use the GTM /data/v1/ path prefix."""

    def test_company_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["company_enrich"] == "/gtm/data/v1/companies/enrich"

    def test_contact_search_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["contact_search"] == "/gtm/data/v1/contacts/search"

    def test_contact_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["contact_enrich"] == "/gtm/data/v1/contacts/enrich"

    def test_intent_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["intent_enrich"] == "/gtm/data/v1/intent/enrich"

    def test_scoops_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["scoops_enrich"] == "/gtm/data/v1/scoops/enrich"

    def test_news_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["news_enrich"] == "/gtm/data/v1/news/enrich"

    def test_tech_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["tech_enrich"] == "/gtm/data/v1/companies/technologies/enrich"


class TestGTMContentType:
    """Validate JSON:API content-type header."""

    def test_content_type_is_jsonapi(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        assert client.headers["Content-Type"] == "application/vnd.api+json"

    def test_accept_includes_jsonapi(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")
        assert "application/vnd.api+json" in client.headers["Accept"]


class TestGTMCompanyEnrichFormat:
    """Validate company enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_company_enrich_sends_jsonapi_payload(self):
        """Company enrich must send JSON:API format with type CompanyEnrich."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {
                "data": [{
                    "type": "Company",
                    "id": "123",
                    "attributes": {
                        "companyName": "Test Corp",
                        "website": "https://test.com",
                        "id": "123",
                    }
                }]
            }

        client._make_request = mock_make_request
        await client.enrich_company(domain="test.com")

        # First payload attempted must be JSON:API format
        assert len(captured_payloads) > 0
        first_payload = captured_payloads[0]
        assert "data" in first_payload, "Payload must use JSON:API data wrapper"
        assert first_payload["data"]["type"] == "CompanyEnrich"
        assert "attributes" in first_payload["data"]


class TestGTMContactSearchFormat:
    """Validate contact search sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_contact_search_sends_jsonapi_payload(self):
        """Contact search must send JSON:API format with type ContactSearch."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {
                "data": [{
                    "type": "Contact",
                    "id": "456",
                    "attributes": {
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "jobTitle": "CTO",
                        "id": "456",
                    }
                }]
            }

        client._make_request = mock_make_request
        await client.search_contacts(domain="test.com", max_results=5)

        # All search payloads must use JSON:API format
        assert len(captured_payloads) > 0
        for call in captured_payloads:
            payload = call["payload"]
            assert "data" in payload, f"Payload must use JSON:API wrapper, got: {list(payload.keys())}"
            assert payload["data"]["type"] == "ContactSearch"
            assert "attributes" in payload["data"]

    @pytest.mark.asyncio
    async def test_contact_search_uses_gtm_endpoint(self):
        """Contact search must use the GTM API endpoint path."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_endpoints = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_endpoints.append(endpoint)
            return {"data": []}

        client._make_request = mock_make_request
        await client.search_contacts(domain="test.com", max_results=5)

        for ep in captured_endpoints:
            assert ep == "/gtm/data/v1/contacts/search", f"Expected GTM endpoint, got: {ep}"


class TestGTMContactEnrichFormat:
    """Validate contact enrich sends JSON:API format with phone outputFields."""

    @pytest.mark.asyncio
    async def test_contact_enrich_sends_jsonapi_payload(self):
        """Contact enrich must send JSON:API format with type ContactEnrich."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {
                "data": [{
                    "type": "Contact",
                    "id": "789",
                    "attributes": {
                        "firstName": "John",
                        "lastName": "Smith",
                        "directPhone": "+1-555-0100",
                        "mobilePhone": "+1-555-0101",
                    }
                }]
            }

        client._make_request = mock_make_request
        await client.enrich_contacts(person_ids=["789"])

        assert len(captured_payloads) > 0
        payload = captured_payloads[0]
        assert "data" in payload, "Must use JSON:API wrapper"
        assert payload["data"]["type"] == "ContactEnrich"
        attrs = payload["data"]["attributes"]
        assert "personId" in attrs or "matchPersonInput" in attrs

    @pytest.mark.asyncio
    async def test_contact_enrich_requests_phone_fields(self):
        """Contact enrich must explicitly request phone outputFields."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request
        await client.enrich_contacts(person_ids=["789"])

        assert len(captured_payloads) > 0
        attrs = captured_payloads[0]["data"]["attributes"]
        output_fields = attrs.get("outputFields", [])
        assert "directPhone" in output_fields, "Must request directPhone"
        assert "mobilePhone" in output_fields, "Must request mobilePhone"
        assert "companyPhone" in output_fields, "Must request companyPhone"

    @pytest.mark.asyncio
    async def test_contact_enrich_no_dnc_filtering(self):
        """Contact enrich must NOT filter out DNC-flagged numbers in our code."""
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            return {
                "data": [{
                    "type": "Contact",
                    "id": "789",
                    "attributes": {
                        "firstName": "John",
                        "lastName": "Smith",
                        "directPhone": "+1-555-0100",
                        "mobilePhone": "+1-555-0101",
                        "directPhoneDoNotCall": True,
                        "mobilePhoneDoNotCall": True,
                    }
                }]
            }

        client._make_request = mock_make_request
        result = await client.enrich_contacts(person_ids=["789"])

        # Phone numbers must be returned even if DNC flagged
        assert result["success"] is True
        assert len(result["people"]) > 0
        person = result["people"][0]
        assert person["direct_phone"] == "+1-555-0100"
        assert person["mobile_phone"] == "+1-555-0101"


class TestGTMIntentEnrichFormat:
    """Validate intent enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_intent_enrich_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.enrich_intent(domain="test.com", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/intent/enrich"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "IntentEnrich"
        attrs = payload["data"]["attributes"]
        assert "topics" in attrs
        assert "companyId" in attrs


class TestGTMScoopsEnrichFormat:
    """Validate scoops enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_scoops_enrich_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.search_scoops(domain="test.com", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/scoops/enrich"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "ScoopEnrich"


class TestGTMNewsEnrichFormat:
    """Validate news enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_news_enrich_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.search_news(company_name="Test Corp", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/news/enrich"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "NewsEnrich"


class TestGTMTechEnrichFormat:
    """Validate technology enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_tech_enrich_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False, params=None):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.enrich_technologies(domain="test.com", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/companies/technologies/enrich"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "TechnologyEnrich"


class TestGTMOAuth2AuthFlow:
    """Validate OAuth2 refresh_token auth is prioritized for GTM API."""

    @pytest.mark.asyncio
    async def test_refresh_token_beats_legacy_auth_even_when_username_set(self):
        """When BOTH refresh_token AND username/password are available, OAuth2
        refresh_token must be tried FIRST — because the legacy /authenticate
        endpoint returns JWTs that DON'T work with GTM API v1 endpoints."""
        from zoominfo_client import ZoomInfoClient, ZOOMINFO_TOKEN_URL

        captured_urls = []

        def make_mock_response(url, **kwargs):
            captured_urls.append(str(url))
            mock_resp = MagicMock()
            if "okta-login" in str(url):
                mock_resp.status_code = 200
                mock_resp.is_success = True
                mock_resp.json.return_value = {
                    "access_token": "oauth2-gtm-token",
                    "refresh_token": "new-rotated-refresh-token",
                    "expires_in": 86400,
                    "token_type": "Bearer",
                }
                mock_resp.raise_for_status = MagicMock()
            else:
                # Legacy /authenticate — should NOT be reached when refresh_token works
                mock_resp.status_code = 200
                mock_resp.is_success = True
                mock_resp.json.return_value = {"jwt": "legacy-jwt-token"}
                mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=make_mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Set BOTH username/password AND refresh_token + client creds
            client = ZoomInfoClient(
                client_id="test-client-id",
                client_secret="test-client-secret",
                username="user@company.com",
                password="password123",
                access_token=None,
            )
            client._refresh_token = "initial-refresh-token"
            client._auto_auth = True

            await client._authenticate()

        # OAuth2 endpoint must be the FIRST URL called, even though username is set
        assert len(captured_urls) > 0
        assert "okta-login" in captured_urls[0], (
            f"First auth call must be Okta OAuth2, not legacy /authenticate. "
            f"Got: {captured_urls[0]}"
        )
        # Must NOT have called legacy /authenticate
        legacy_calls = [u for u in captured_urls if "/authenticate" in u and "okta" not in u]
        assert len(legacy_calls) == 0, (
            f"Legacy /authenticate must not be called when refresh_token succeeds. "
            f"Calls: {captured_urls}"
        )
        # Token must be the OAuth2 one, not the legacy JWT
        assert client.access_token == "oauth2-gtm-token"

    @pytest.mark.asyncio
    async def test_refresh_token_rotation_stored(self):
        """After successful OAuth2 refresh, new refresh_token must be stored."""
        from zoominfo_client import ZoomInfoClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "rotated-refresh-token-xyz",
            "expires_in": 86400,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "old-refresh-token"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                client = ZoomInfoClient(
                    client_id="cid",
                    client_secret="csecret",
                )

                await client._authenticate()

        assert client._refresh_token == "rotated-refresh-token-xyz"
        assert client.access_token == "new-access-token"

    @pytest.mark.asyncio
    async def test_oauth2_token_lifetime_24h(self):
        """OAuth2 access tokens are valid for 24 hours (86400s), not 1 hour."""
        import time
        from zoominfo_client import ZoomInfoClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = {
            "access_token": "token-24h",
            "refresh_token": "rt",
            "expires_in": 86400,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"ZOOMINFO_REFRESH_TOKEN": "rt"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                client = ZoomInfoClient(
                    client_id="cid",
                    client_secret="csecret",
                )

                before = time.time()
                await client._authenticate()

        # Token should expire ~24h from now (minus 300s buffer)
        expected_min = before + 86400 - 300 - 5  # 5s tolerance
        expected_max = before + 86400 - 300 + 5
        assert expected_min <= client._token_expires_at <= expected_max, (
            f"Token expiry should be ~24h out, got offset: "
            f"{client._token_expires_at - before}s"
        )

    def test_legacy_authenticate_not_called_when_no_username(self):
        """If ZOOMINFO_USERNAME is not set, legacy /authenticate is never attempted."""
        from zoominfo_client import ZoomInfoClient
        with patch.dict("os.environ", {}, clear=True):
            client = ZoomInfoClient(access_token="manual-oauth-token")
        # username/password should not be set
        assert not client._username
        assert not client._password

    @pytest.mark.asyncio
    async def test_static_token_fallback_when_no_refresh_token(self):
        """When only a static access_token is provided (no refresh_token),
        it should be used directly without any auth calls."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="manual-oauth2-bearer-token")
        assert client.access_token == "manual-oauth2-bearer-token"
        assert client.headers["Authorization"] == "Bearer manual-oauth2-bearer-token"
