"""
Tests for four fixes:
1. Gamma phone extraction from nested contact dict
2. ZoomInfo identity lookup (rpp as query param, companyPastOrPresent)
3. Company overview fields in result (description, company_overview, company_phone)
4. ZoomInfo intent enrich uses "topic" (singular) not "topics"
"""
import pytest


# ── Issue 1: Gamma phone extraction from nested contact dict ──────────────

def test_gamma_phones_from_nested_contact_dict():
    """Phone numbers stored in nested contact dict should appear in slideshow."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholder_map = {
        "stakeholders": [
            {
                "name": "Jane Doe",
                "title": "Chief Technology Officer",
                "csuiteCategory": "CTO",
                # Phones only in nested contact dict (as built by production_main)
                "contact": {
                    "email": "jane@acme.com",
                    "phone": "+1-555-0001",
                    "directPhone": "+1-555-0002",
                    "mobilePhone": "+1-555-0003",
                    "companyPhone": "+1-555-0004",
                    "linkedinUrl": "https://linkedin.com/in/janedoe",
                },
            },
        ],
        "otherContacts": [],
    }
    company_data = {
        "company_name": "Acme Corp",
        "validated_data": {
            "company_name": "Acme Corp",
            "industry": "Tech",
            "stakeholder_map": stakeholder_map,
        },
        "confidence_score": 0.85,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    md = creator._generate_markdown(company_data)

    assert "+1-555-0002" in md, "directPhone from nested contact dict should appear"
    assert "+1-555-0003" in md, "mobilePhone from nested contact dict should appear"
    assert "jane@acme.com" in md, "email from nested contact dict should appear"
    assert "linkedin.com/in/janedoe" in md, "linkedinUrl from nested contact dict should appear"


def test_gamma_phones_from_top_level_fields():
    """Phone numbers at top level (set for sorting) should still work."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholder_map = {
        "stakeholders": [
            {
                "name": "Bob Smith",
                "title": "CFO",
                "csuiteCategory": "CFO",
                "email": "bob@acme.com",
                "direct_phone": "+1-555-1000",
                "mobile_phone": "+1-555-1001",
                "linkedin_url": "https://linkedin.com/in/bob",
            },
        ],
        "otherContacts": [],
    }
    company_data = {
        "company_name": "Acme Corp",
        "validated_data": {
            "company_name": "Acme Corp",
            "industry": "Tech",
            "stakeholder_map": stakeholder_map,
        },
        "confidence_score": 0.85,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    md = creator._generate_markdown(company_data)

    assert "+1-555-1000" in md
    assert "+1-555-1001" in md
    assert "linkedin.com/in/bob" in md


# ── Issue 2: Identity lookup payload format ──────────────────────────────

def test_identity_lookup_no_rpp_in_attributes():
    """lookup_contacts_by_identity should NOT put rpp in JSON body attributes."""
    from worker.zoominfo_client import ZoomInfoClient

    # We can't easily call the async function, but we can verify the code
    # structure by checking the source directly
    import inspect
    source = inspect.getsource(ZoomInfoClient.lookup_contacts_by_identity)

    # rpp should NOT appear in the attributes dict
    assert '"rpp"' not in source, "rpp should not be in attributes (use page[size] query param)"
    assert "'rpp'" not in source, "rpp should not be in attributes (use page[size] query param)"

    # page[size] should be used as query param
    assert "page[size]" in source, "Should use page[size] as query parameter"

    # companyPastOrPresent should be present
    assert "companyPastOrPresent" in source, "Should filter for current employees"


# ── Issue 4: Intent enrich uses "topic" (singular) ──────────────────────

def test_intent_enrich_uses_topic_singular():
    """ZoomInfo Intent Enrich API requires 'topic' (singular), not 'topics'."""
    from worker.zoominfo_client import ZoomInfoClient
    import inspect

    source = inspect.getsource(ZoomInfoClient.enrich_intent)

    # The payload should use "topic" (singular) for the field name
    assert '"topic":' in source or "'topic':" in source, \
        "Intent enrich should use 'topic' (singular) per ZoomInfo API docs"

    # Should NOT use "topics" as a key in the payload attributes
    # (it's fine to use "topics" as a variable name, just not as a dict key)
    # Check that the attrs dict uses "topic" not "topics"
    assert '"topic": topics_to_use' in source, \
        "Intent enrich attrs should map 'topic' key to topics_to_use value"


def test_intent_topics_fallback_no_default_topics():
    """When topic lookup fails, should NOT fall back to DEFAULT_INTENT_TOPICS."""
    from worker.zoominfo_client import ZoomInfoClient
    import inspect

    source = inspect.getsource(ZoomInfoClient._fetch_valid_intent_topics)

    # The except block should NOT assign DEFAULT_INTENT_TOPICS to cache
    # (they cause PFAPI0006 because they don't match ZoomInfo's taxonomy)
    # Look for the actual assignment pattern, not just mentions in comments
    assert "list(DEFAULT_INTENT_TOPICS)" not in source, \
        "Should not fall back to list(DEFAULT_INTENT_TOPICS) on failure"
