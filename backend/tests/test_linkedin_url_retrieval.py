"""
Tests for LinkedIn URL retrieval and contact validation pipeline.
TDD: Tests written FIRST before implementation.

Covers:
1. ZoomInfo search does NOT send outputFields (causes HTTP 400)
2. ZoomInfo enrich tries extended fields (with linkedinUrl) then falls back
3. LinkedIn URLs flow through merge into stakeholders
4. LLM fact checker enforces: LinkedIn mandatory + at least one phone/email
5. Contacts without LinkedIn are filtered pre-LLM
6. Debug data includes LinkedIn URLs per contact
"""
import pytest
import asyncio
import os
import sys
import json
from unittest.mock import AsyncMock, patch, MagicMock

# Add worker directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestZoomInfoSearchNoOutputFields:
    """ZoomInfo contact search must NOT include outputFields (causes HTTP 400)."""

    @pytest.mark.asyncio
    async def test_search_contacts_does_not_send_output_fields(self):
        """search_contacts must NOT send outputFields — it's invalid on the search endpoint."""
        from zoominfo_client import ZoomInfoClient

        client = ZoomInfoClient(access_token="test-token")

        captured_payloads = []

        async def mock_make_request(endpoint, payload, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        await client.search_contacts(domain="example.com", max_results=5)

        assert len(captured_payloads) > 0, "No search requests were made"
        for payload in captured_payloads:
            attrs = payload.get("data", {}).get("attributes", {})
            assert "outputFields" not in attrs, (
                f"search_contacts must NOT include outputFields (causes HTTP 400). "
                f"Found outputFields={attrs.get('outputFields')} in payload"
            )


class TestZoomInfoEnrichWithLinkedIn:
    """ZoomInfo contact enrich should try to get linkedinUrl with fallback."""

    def test_extended_enrich_fields_includes_linkedin(self):
        """EXTENDED enrich output fields should include linkedinUrl."""
        from zoominfo_client import CONTACT_ENRICH_EXTENDED_FIELDS
        assert "linkedinUrl" in CONTACT_ENRICH_EXTENDED_FIELDS

    def test_base_enrich_fields_excludes_linkedin(self):
        """BASE enrich output fields should NOT include linkedinUrl (known disallowed)."""
        from zoominfo_client import CONTACT_ENRICH_OUTPUT_FIELDS
        assert "linkedinUrl" not in CONTACT_ENRICH_OUTPUT_FIELDS

    @pytest.mark.asyncio
    async def test_enrich_tries_extended_then_falls_back(self):
        """enrich_contacts tries extended fields first, falls back to base on HTTP 400."""
        from zoominfo_client import ZoomInfoClient
        import httpx

        client = ZoomInfoClient(access_token="test-token")
        call_count = 0

        async def mock_make_request(endpoint, payload, params=None):
            nonlocal call_count
            call_count += 1
            attrs = payload.get("data", {}).get("attributes", {})
            output_fields = attrs.get("outputFields", [])

            if "linkedinUrl" in output_fields:
                # First call with extended fields — simulate PFAPI0005
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "PFAPI0005: Invalid field requested: linkedinUrl"
                mock_response.json.return_value = {"errors": [{"code": "PFAPI0005"}]}
                raise httpx.HTTPStatusError(
                    "400", request=MagicMock(), response=mock_response
                )
            else:
                # Second call with base fields — return success
                return {
                    "data": [
                        {
                            "id": "123",
                            "attributes": {
                                "firstName": "Jane",
                                "lastName": "Smith",
                                "email": "jane@test.com",
                                "phone": "+1-555-1234",
                            }
                        }
                    ]
                }

        client._make_request = mock_make_request

        result = await client.enrich_contacts(person_ids=["123"])

        assert result["success"] is True, f"Enrich failed: {result.get('error')}"
        assert call_count == 2, f"Expected 2 calls (extended then base), got {call_count}"
        assert len(result["people"]) == 1


class TestLinkedInInNormalizedContact:
    """_normalize_contact must extract LinkedIn URL from ZoomInfo response."""

    def test_normalize_contact_extracts_linkedin(self):
        from zoominfo_client import ZoomInfoClient

        raw_contact = {
            "attributes": {
                "firstName": "Jane",
                "lastName": "Smith",
                "jobTitle": "CTO",
                "linkedinUrl": "https://www.linkedin.com/in/janesmith",
                "email": "jane@example.com",
            }
        }
        result = ZoomInfoClient._normalize_contact(raw_contact)
        assert result["linkedin"] == "https://www.linkedin.com/in/janesmith"

    def test_normalize_contact_handles_missing_linkedin(self):
        from zoominfo_client import ZoomInfoClient

        raw_contact = {"attributes": {"firstName": "John", "lastName": "Doe"}}
        result = ZoomInfoClient._normalize_contact(raw_contact)
        assert result["linkedin"] == ""


class TestContactValidationRules:
    """Contacts must have LinkedIn + at least one of phone/email to be included."""

    @pytest.mark.asyncio
    async def test_contacts_without_linkedin_are_filtered(self):
        """Contacts with no LinkedIn URL should be filtered out pre-LLM."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "No LinkedIn Guy",
                "title": "CTO",
                "email": "guy@test.com",
                "phone": "+1-555-1234",
                # No linkedin_url
            },
            {
                "name": "Has LinkedIn Gal",
                "title": "CFO",
                "email": "gal@test.com",
                "linkedin_url": "https://linkedin.com/in/gal",
            },
        ]

        async def mock_openai(prompt, system_msg):
            return {
                "contacts": [
                    {"name": "Has LinkedIn Gal", "fact_check_score": 0.9, "fact_check_notes": "Verified"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            result = await fact_check_contacts("Test Corp", "test.com", contacts)

        names = [c["name"] for c in result]
        assert "No LinkedIn Guy" not in names, "Contact without LinkedIn should be filtered out"
        assert "Has LinkedIn Gal" in names

    @pytest.mark.asyncio
    async def test_contacts_with_linkedin_but_no_phone_or_email_filtered(self):
        """Contacts with LinkedIn but no phone AND no email should be filtered."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "LinkedIn Only Person",
                "title": "VP Engineering",
                "linkedin_url": "https://linkedin.com/in/linonly",
                # No phone, no email
            },
            {
                "name": "Complete Contact",
                "title": "CTO",
                "email": "complete@test.com",
                "linkedin_url": "https://linkedin.com/in/complete",
            },
        ]

        async def mock_openai(prompt, system_msg):
            return {
                "contacts": [
                    {"name": "Complete Contact", "fact_check_score": 0.9, "fact_check_notes": "Verified"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            result = await fact_check_contacts("Test Corp", "test.com", contacts)

        names = [c["name"] for c in result]
        assert "LinkedIn Only Person" not in names, (
            "Contact with LinkedIn but no phone/email should be filtered"
        )
        assert "Complete Contact" in names

    @pytest.mark.asyncio
    async def test_contact_with_linkedin_and_phone_passes(self):
        """Contact with LinkedIn + phone (no email) should pass."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "Phone Person",
                "title": "CTO",
                "direct_phone": "+1-555-1234",
                "linkedin_url": "https://linkedin.com/in/phoneperson",
            },
        ]

        async def mock_openai(prompt, system_msg):
            return {
                "contacts": [
                    {"name": "Phone Person", "fact_check_score": 0.95, "fact_check_notes": "Verified current CTO"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            result = await fact_check_contacts("Test Corp", "test.com", contacts)

        assert len(result) == 1
        assert result[0]["name"] == "Phone Person"

    @pytest.mark.asyncio
    async def test_llm_verifies_current_employment(self):
        """LLM prompt must check current employment at the company."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "Jane Smith",
                "title": "CTO",
                "email": "jane@test.com",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        ]

        captured_prompts = []

        async def mock_openai(prompt, system_msg):
            captured_prompts.append(prompt)
            return {
                "contacts": [
                    {"name": "Jane Smith", "fact_check_score": 0.9, "fact_check_notes": "Verified"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            await fact_check_contacts("Test Corp", "test.com", contacts)

        assert len(captured_prompts) > 0
        prompt = captured_prompts[0]
        assert "current" in prompt.lower(), "Prompt must verify CURRENT employment"
        assert "linkedin" in prompt.lower(), "Prompt must reference LinkedIn for verification"
        assert "decision maker" in prompt.lower() or "decision-maker" in prompt.lower(), (
            "Prompt must verify the contact is a decision maker"
        )


class TestLinkedInInDebugMode:
    """Debug mode must show LinkedIn URLs in ZoomInfo contact enrichment data."""

    def test_per_contact_enrichment_includes_linkedin(self):
        from production_main import generate_debug_data
        from datetime import datetime

        job_data = {
            "company_data": {"company_name": "Test Corp", "domain": "test.com"},
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "apollo_data": {},
            "pdl_data": {},
            "hunter_data": {},
            "news_data": {},
            "orchestrator_data": {},
            "zoominfo_data": {
                "contacts": [
                    {
                        "name": "Jane Smith",
                        "title": "CTO",
                        "linkedin": "https://linkedin.com/in/janesmith",
                        "enriched": True,
                        "direct_phone": "+1-555-1234",
                        "contact_accuracy_score": 90,
                    }
                ],
            },
            "result": {"validated_data": {}},
            "api_calls": [],
            "fact_check_results": {},
        }

        debug = generate_debug_data("test-job", job_data)

        step_1d = None
        for step in debug["process_steps"]:
            if step["id"] == "step-1d":
                step_1d = step
                break

        assert step_1d is not None
        per_contact = step_1d["metadata"]["per_contact_enrichment"]
        assert len(per_contact) > 0
        contact = per_contact[0]
        assert "has_linkedin_url" in contact
        assert "linkedin_url" in contact
        assert contact["has_linkedin_url"] is True
        assert contact["linkedin_url"] == "https://linkedin.com/in/janesmith"


class TestMergeZoomInfoContactsLinkedIn:
    """_merge_zoominfo_contacts must transfer LinkedIn URLs."""

    def test_merge_transfers_linkedin_from_zoominfo(self):
        from production_main import _merge_zoominfo_contacts

        stakeholders = [
            {"name": "Jane Smith", "title": "CTO", "email": "jane@test.com"}
        ]
        zi_contacts = [
            {
                "name": "Jane Smith",
                "title": "CTO",
                "email": "jane@test.com",
                "linkedin": "https://linkedin.com/in/janesmith",
                "direct_phone": "+1-555-1234",
            }
        ]

        result = _merge_zoominfo_contacts(stakeholders, zi_contacts)
        assert result[0].get("linkedin_url") == "https://linkedin.com/in/janesmith"

    def test_new_zoominfo_contact_gets_linkedin(self):
        from production_main import _merge_zoominfo_contacts

        stakeholders = []
        zi_contacts = [
            {
                "name": "New Person",
                "title": "VP Engineering",
                "email": "new@test.com",
                "linkedin": "https://linkedin.com/in/newperson",
            }
        ]

        result = _merge_zoominfo_contacts(stakeholders, zi_contacts)
        assert len(result) == 1
        assert result[0].get("linkedin_url") == "https://linkedin.com/in/newperson"


class TestContactEnrichEndpointLinkedIn:
    """GET /contacts/enrich/{domain} must return linkedinUrl for each contact."""

    def test_endpoint_returns_linkedin_url(self):
        from production_main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Jane Smith",
                "title": "CTO",
                "email": "jane@test.com",
                "linkedin": "https://linkedin.com/in/janesmith",
                "direct_phone": "+1-555-1234",
                "contact_accuracy_score": 90,
            }
        ]

        mock_zi = AsyncMock()
        mock_zi.search_and_enrich_contacts = AsyncMock(
            return_value={"success": True, "people": mock_contacts, "error": None}
        )

        with patch("production_main._get_zoominfo_client", return_value=mock_zi):
            response = client.get("/contacts/enrich/test.com")

        assert response.status_code == 200
        data = response.json()
        assert len(data["contacts"]) == 1
        assert data["contacts"][0]["linkedinUrl"] == "https://linkedin.com/in/janesmith"
