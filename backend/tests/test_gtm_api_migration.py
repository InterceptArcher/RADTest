"""
Tests for ZoomInfo GTM API v1 migration.
TDD: Tests written FIRST — validates endpoint paths, JSON:API request format,
content-type headers, and phone field output configuration.

These tests MUST FAIL against the old legacy endpoint code and PASS after migration.
"""
import pytest
import os
import sys
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

    def test_scoops_search_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["scoops_search"] == "/gtm/data/v1/scoops/search"

    def test_news_search_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["news_search"] == "/gtm/data/v1/news/search"

    def test_tech_enrich_endpoint(self):
        from zoominfo_client import ENDPOINTS
        assert ENDPOINTS["tech_enrich"] == "/gtm/data/v1/technologies/enrich"


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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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

        async def mock_make_request(endpoint, payload, _is_retry=False):
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


class TestGTMScoopsSearchFormat:
    """Validate scoops search sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_scoops_search_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.search_scoops(domain="test.com", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/scoops/search"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "ScoopsSearch"


class TestGTMNewsSearchFormat:
    """Validate news search sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_news_search_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.search_news(company_name="Test Corp", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/news/search"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "NewsSearch"


class TestGTMTechEnrichFormat:
    """Validate technology enrich sends JSON:API format."""

    @pytest.mark.asyncio
    async def test_tech_enrich_sends_jsonapi_payload(self):
        from zoominfo_client import ZoomInfoClient
        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, _is_retry=False):
            captured_payloads.append({"endpoint": endpoint, "payload": payload})
            return {"data": []}

        client._make_request = mock_make_request
        await client.enrich_technologies(domain="test.com", company_id="123")

        assert len(captured_payloads) > 0
        call = captured_payloads[0]
        assert call["endpoint"] == "/gtm/data/v1/technologies/enrich"
        payload = call["payload"]
        assert "data" in payload
        assert payload["data"]["type"] == "TechnologiesEnrich"
