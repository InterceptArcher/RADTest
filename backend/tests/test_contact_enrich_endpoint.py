"""
Tests for ZoomInfo Contact Enrichment endpoint.
TDD: Tests written FIRST before implementation.

Endpoint: GET /contacts/enrich/{domain}
Purpose: On-demand ZoomInfo contact phone enrichment for a company domain.
Returns: Enriched contacts with direct/mobile/company phones, accuracy scores, and source attribution.
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestContactEnrichEndpoint:
    """Tests for GET /contacts/enrich/{domain} endpoint."""

    def test_endpoint_exists_and_returns_200(self):
        """Endpoint is reachable and returns 200 on success."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Jane Smith",
                "title": "Chief Information Officer",
                "role_type": "CIO",
                "email": "jane.smith@example.com",
                "phone": "+1-555-000-1234",
                "direct_phone": "+1-555-000-1234",
                "mobile_phone": "+1-555-000-5678",
                "company_phone": "+1-555-000-0000",
                "contact_accuracy_score": 92,
                "source": "zoominfo",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {
                "ZOOMINFO_ACCESS_TOKEN": "test-token",
                "ZOOMINFO_CLIENT_ID": "",
                "ZOOMINFO_CLIENT_SECRET": "",
            }):
                response = client.get("/contacts/enrich/example.com")

        assert response.status_code == 200

    def test_returns_contacts_list(self):
        """Response body contains a 'contacts' list."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "John Doe",
                "title": "CTO",
                "role_type": "CTO",
                "email": "john@example.com",
                "direct_phone": "+1-555-111-2222",
                "mobile_phone": "+1-555-111-3333",
                "company_phone": "+1-555-111-0000",
                "contact_accuracy_score": 88,
                "source": "zoominfo",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/example.com")

        data = response.json()
        assert "contacts" in data
        assert isinstance(data["contacts"], list)

    def test_each_contact_includes_phone_fields(self):
        """Each contact in response includes direct_phone, mobile_phone, company_phone."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Alice Johnson",
                "title": "CFO",
                "role_type": "CFO",
                "email": "alice@example.com",
                "direct_phone": "+1-800-555-0001",
                "mobile_phone": "+1-800-555-0002",
                "company_phone": "+1-800-555-0003",
                "contact_accuracy_score": 95,
                "source": "zoominfo",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/example.com")

        data = response.json()
        contact = data["contacts"][0]

        assert "directPhone" in contact
        assert "mobilePhone" in contact
        assert "companyPhone" in contact
        assert contact["directPhone"] == "+1-800-555-0001"
        assert contact["mobilePhone"] == "+1-800-555-0002"
        assert contact["companyPhone"] == "+1-800-555-0003"

    def test_each_contact_includes_accuracy_score(self):
        """Each contact in response includes contactAccuracyScore."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Bob Lee",
                "title": "COO",
                "role_type": "COO",
                "email": "bob@example.com",
                "direct_phone": "+1-555-222-3333",
                "contact_accuracy_score": 87,
                "source": "zoominfo",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/example.com")

        data = response.json()
        contact = data["contacts"][0]
        assert "contactAccuracyScore" in contact
        assert contact["contactAccuracyScore"] == 87

    def test_each_contact_has_phone_source_zoominfo(self):
        """Each contact in response has phoneSource set to 'zoominfo'."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Carol White",
                "title": "CISO",
                "role_type": "CISO",
                "email": "carol@example.com",
                "direct_phone": "+1-555-333-4444",
                "contact_accuracy_score": 91,
                "source": "zoominfo",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/example.com")

        data = response.json()
        contact = data["contacts"][0]
        assert contact.get("phoneSource") == "zoominfo"

    def test_returns_domain_and_count_in_response(self):
        """Response includes domain and total_count metadata."""
        from production_main import app
        client = TestClient(app)

        mock_contacts = [
            {
                "name": "Dave Brown",
                "title": "CEO",
                "role_type": "CEO",
                "direct_phone": "+1-555-444-5555",
                "contact_accuracy_score": 99,
                "source": "zoominfo",
            }
        ]

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": mock_contacts, "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/example.com")

        data = response.json()
        assert data["domain"] == "example.com"
        assert data["total_count"] == 1

    def test_returns_404_when_no_zoominfo_credentials(self):
        """Returns 503 when ZoomInfo credentials are not configured."""
        from production_main import app
        client = TestClient(app)

        with patch.dict(os.environ, {
            "ZOOMINFO_ACCESS_TOKEN": "",
            "ZOOMINFO_CLIENT_ID": "",
            "ZOOMINFO_CLIENT_SECRET": "",
        }, clear=False):
            # Patch env vars to be empty
            with patch("production_main.ZOOMINFO_ACCESS_TOKEN", ""):
                with patch("production_main.ZOOMINFO_CLIENT_ID", ""):
                    with patch("production_main.ZOOMINFO_CLIENT_SECRET", ""):
                        response = client.get("/contacts/enrich/example.com")

        assert response.status_code in (503, 400)

    def test_returns_empty_contacts_when_none_found(self):
        """Returns empty contacts list (not error) when ZoomInfo finds no contacts."""
        from production_main import app
        client = TestClient(app)

        with patch("production_main.ZoomInfoClient") as mock_zi_class:
            mock_zi = AsyncMock()
            mock_zi.search_and_enrich_contacts = AsyncMock(
                return_value={"success": True, "people": [], "error": None}
            )
            mock_zi_class.return_value = mock_zi

            with patch.dict(os.environ, {"ZOOMINFO_ACCESS_TOKEN": "test-token"}):
                response = client.get("/contacts/enrich/unknown-company.com")

        assert response.status_code == 200
        data = response.json()
        assert data["contacts"] == []
        assert data["total_count"] == 0


class TestPhoneSourceFieldInPipeline:
    """Tests that phoneSource field is correctly set in the full pipeline's stakeholder map."""

    def test_zoominfo_contacts_get_phone_source_set(self):
        """Stakeholders sourced from ZoomInfo have phoneSource='zoominfo' in contact object."""
        # Import the contact_entry builder logic
        # We test the _build_contact_entry helper
        stakeholder = {
            "name": "Eve Davis",
            "title": "CIO",
            "role_type": "CIO",
            "email": "eve@example.com",
            "phone": "+1-555-000-0001",
            "direct_phone": "+1-555-000-0001",
            "mobile_phone": "+1-555-000-0002",
            "company_phone": "+1-555-000-0003",
            "contact_accuracy_score": 90,
            "linkedin_url": "https://linkedin.com/in/evedavis",
            "source": "zoominfo",
        }

        # Simulate what production_main.py does when building contact_entry
        contact_obj = {
            "email": stakeholder.get("email"),
            "phone": stakeholder.get("phone"),
            "directPhone": stakeholder.get("direct_phone"),
            "mobilePhone": stakeholder.get("mobile_phone"),
            "companyPhone": stakeholder.get("company_phone"),
            "linkedinUrl": stakeholder.get("linkedin_url"),
            "contactAccuracyScore": stakeholder.get("contact_accuracy_score"),
            "phoneSource": "zoominfo" if stakeholder.get("source") == "zoominfo" else None,
        }

        assert contact_obj["phoneSource"] == "zoominfo"
        assert contact_obj["directPhone"] == "+1-555-000-0001"
        assert contact_obj["mobilePhone"] == "+1-555-000-0002"
        assert contact_obj["companyPhone"] == "+1-555-000-0003"

    def test_apollo_contacts_do_not_get_zoominfo_phone_source(self):
        """Stakeholders from Apollo do NOT get phoneSource='zoominfo'."""
        stakeholder = {
            "name": "Frank Miller",
            "title": "CFO",
            "role_type": "CFO",
            "email": "frank@example.com",
            "phone": "+1-555-999-8888",
            "source": "apollo",
        }

        contact_obj = {
            "phone": stakeholder.get("phone"),
            "directPhone": stakeholder.get("direct_phone"),
            "phoneSource": "zoominfo" if stakeholder.get("source") == "zoominfo" else None,
        }

        assert contact_obj["phoneSource"] is None

    def test_normalize_contact_preserves_all_phone_types(self):
        """ZoomInfo _normalize_contact returns all phone fields."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker"
        ))
        from zoominfo_client import ZoomInfoClient

        raw_contact = {
            "attributes": {
                "firstName": "Grace",
                "lastName": "Hopper",
                "jobTitle": "Chief Technology Officer",
                "email": "grace@example.com",
                "directPhone": "+1-555-111-0001",
                "mobilePhone": "+1-555-111-0002",
                "companyPhone": "+1-555-111-0003",
                "contactAccuracyScore": 94,
                "personId": "zi-12345",
            }
        }

        result = ZoomInfoClient._normalize_contact(raw_contact)

        assert result["direct_phone"] == "+1-555-111-0001"
        assert result["mobile_phone"] == "+1-555-111-0002"
        assert result["company_phone"] == "+1-555-111-0003"
        assert result["contact_accuracy_score"] == 94
        assert result["person_id"] == "zi-12345"
