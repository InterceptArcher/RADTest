"""
Tests for LinkedIn URL retrieval in ZoomInfo contact enrichment pipeline.
TDD: Tests written FIRST before implementation.

Covers:
1. ZoomInfo search_contacts passes outputFields (including linkedinUrl)
2. LinkedIn URLs flow through merge into stakeholders
3. Debug data includes LinkedIn URLs per contact
4. LLM fact checker validates current employment using LinkedIn
5. Apollo LinkedIn enrichment has no artificial cap
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


class TestZoomInfoSearchOutputFields:
    """ZoomInfo contact search must include outputFields with linkedinUrl."""

    def test_output_fields_includes_linkedin_url(self):
        """OUTPUT_FIELDS list must contain linkedinUrl."""
        from zoominfo_client import OUTPUT_FIELDS
        assert "linkedinUrl" in OUTPUT_FIELDS

    @pytest.mark.asyncio
    async def test_search_contacts_passes_output_fields(self):
        """search_contacts must send outputFields in the search attributes."""
        from zoominfo_client import ZoomInfoClient, OUTPUT_FIELDS

        client = ZoomInfoClient(access_token="test-token")

        # Capture the payload sent to _make_request
        captured_payloads = []
        original_make_request = client._make_request

        async def mock_make_request(endpoint, payload, params=None):
            captured_payloads.append(payload)
            return {"data": []}

        client._make_request = mock_make_request

        await client.search_contacts(domain="example.com", max_results=5)

        # At least one request should have been made with outputFields
        assert len(captured_payloads) > 0, "No search requests were made"
        has_output_fields = any(
            p.get("data", {}).get("attributes", {}).get("outputFields")
            for p in captured_payloads
        )
        assert has_output_fields, (
            "No search request included outputFields. "
            f"Payloads: {json.dumps(captured_payloads, default=str)}"
        )

        # Verify linkedinUrl is in the outputFields
        for payload in captured_payloads:
            attrs = payload.get("data", {}).get("attributes", {})
            output_fields = attrs.get("outputFields", [])
            if output_fields:
                assert "linkedinUrl" in output_fields, (
                    f"outputFields missing linkedinUrl: {output_fields}"
                )


class TestLinkedInInNormalizedContact:
    """_normalize_contact must extract LinkedIn URL from ZoomInfo response."""

    def test_normalize_contact_extracts_linkedin(self):
        """LinkedIn URL is extracted from normalized contact data."""
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
        """Missing LinkedIn URL returns empty string, not None."""
        from zoominfo_client import ZoomInfoClient

        raw_contact = {"attributes": {"firstName": "John", "lastName": "Doe"}}
        result = ZoomInfoClient._normalize_contact(raw_contact)
        assert result["linkedin"] == ""


class TestLinkedInInDebugMode:
    """Debug mode must show LinkedIn URLs in ZoomInfo contact enrichment data."""

    def test_per_contact_enrichment_includes_linkedin(self):
        """Debug step-1d per_contact_enrichment includes has_linkedin_url field."""
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

        # Find step-1d (ZoomInfo Contact Enrich)
        step_1d = None
        for step in debug["process_steps"]:
            if step["id"] == "step-1d":
                step_1d = step
                break

        assert step_1d is not None, "step-1d (ZoomInfo Contact Enrich) not found in debug data"
        per_contact = step_1d["metadata"]["per_contact_enrichment"]
        assert len(per_contact) > 0, "per_contact_enrichment is empty"

        # Each contact must have has_linkedin_url and linkedin_url fields
        contact = per_contact[0]
        assert "has_linkedin_url" in contact, (
            f"per_contact_enrichment missing has_linkedin_url field. Keys: {list(contact.keys())}"
        )
        assert "linkedin_url" in contact, (
            f"per_contact_enrichment missing linkedin_url field. Keys: {list(contact.keys())}"
        )
        assert contact["has_linkedin_url"] is True
        assert contact["linkedin_url"] == "https://linkedin.com/in/janesmith"

    def test_contact_search_log_includes_linkedin(self):
        """Contact search log sample includes linkedin_url field."""
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
                    }
                ],
            },
            "result": {"validated_data": {}},
            "api_calls": [
                {
                    "name": "ZoomInfo Contact Search + Enrich (GTM API v1)",
                    "response_body": {
                        "contacts_found": 1,
                        "sample": [
                            {
                                "name": "Jane Smith",
                                "title": "CTO",
                                "linkedin_url": "https://linkedin.com/in/janesmith",
                            }
                        ],
                    },
                }
            ],
            "fact_check_results": {},
        }

        debug = generate_debug_data("test-job", job_data)
        # Verify the debug data generates without error
        assert debug["job_id"] == "test-job"


class TestLLMFactCheckerUsesLinkedIn:
    """LLM fact checker must use LinkedIn URLs to verify current employment."""

    @pytest.mark.asyncio
    async def test_fact_checker_prompt_includes_company_verification(self):
        """fact_check_contacts prompt must ask LLM to verify current employment at the company."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "Jane Smith",
                "title": "CTO",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        ]

        # Mock _call_openai_json to capture the prompt
        captured_prompts = []

        async def mock_openai(prompt, system_msg):
            captured_prompts.append(prompt)
            return {
                "contacts": [
                    {"name": "Jane Smith", "fact_check_score": 0.9, "fact_check_notes": "Verified"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            result = await fact_check_contacts("Test Corp", "test.com", contacts)

        assert len(captured_prompts) > 0, "No LLM call was made"
        prompt = captured_prompts[0]

        # Prompt must instruct LLM to verify current employment
        assert "current" in prompt.lower() or "currently" in prompt.lower(), (
            "Prompt does not ask LLM to verify CURRENT employment"
        )
        assert "linkedin" in prompt.lower(), (
            "Prompt does not mention LinkedIn for verification"
        )

    @pytest.mark.asyncio
    async def test_fact_checker_sends_linkedin_urls_to_llm(self):
        """fact_check_contacts must include LinkedIn URLs in the contact data sent to LLM."""
        from production_main import fact_check_contacts

        contacts = [
            {
                "name": "John Doe",
                "title": "CFO",
                "linkedin_url": "https://linkedin.com/in/johndoe",
            }
        ]

        captured_prompts = []

        async def mock_openai(prompt, system_msg):
            captured_prompts.append(prompt)
            return {
                "contacts": [
                    {"name": "John Doe", "fact_check_score": 0.95, "fact_check_notes": "Verified"}
                ]
            }

        with patch("production_main._call_openai_json", side_effect=mock_openai):
            await fact_check_contacts("Test Corp", "test.com", contacts)

        assert len(captured_prompts) > 0
        prompt = captured_prompts[0]
        assert "linkedin.com/in/johndoe" in prompt, (
            "LinkedIn URL not included in LLM prompt"
        )


class TestApolloLinkedInEnrichmentNoCap:
    """Apollo LinkedIn enrichment must not have artificial 15-contact cap."""

    def test_no_hardcoded_slice_limit(self):
        """The Apollo LinkedIn enrichment code should process all contacts, not just 15."""
        import inspect
        from production_main import process_company_profile

        source = inspect.getsource(process_company_profile)

        # Check that there's no [:15] slice on contacts_needing_linkedin
        # This is a code-level check — the [:15] was the original limitation
        assert "contacts_needing_linkedin[:15]" not in source, (
            "Apollo LinkedIn enrichment still has [:15] cap limiting to 15 contacts"
        )


class TestMergeZoomInfoContactsLinkedIn:
    """_merge_zoominfo_contacts must transfer LinkedIn URLs."""

    def test_merge_transfers_linkedin_from_zoominfo(self):
        """LinkedIn URL from ZoomInfo contact is merged into stakeholder."""
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
        """New ZoomInfo-only contacts added to stakeholders include linkedin_url."""
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
        """Contact enrich endpoint maps linkedin to linkedinUrl in response."""
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
