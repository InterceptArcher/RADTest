"""
Tests for individual stakeholder slides in Gamma slideshow.
Each contact in stakeholder_map.stakeholders should get their own dedicated slide.
"""
import pytest
from worker.gamma_slideshow import GammaSlideshowCreator


def _make_company_data(stakeholder_map=None, stakeholder_profiles=None):
    """Helper to build company_data with stakeholder sources."""
    data = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
            "industry": "Technology",
        },
        "confidence_score": 0.85,
    }
    if stakeholder_map is not None:
        data["validated_data"]["stakeholder_map"] = stakeholder_map
    if stakeholder_profiles is not None:
        data["validated_data"]["stakeholder_profiles"] = stakeholder_profiles
    return data


def test_each_stakeholder_gets_own_slide():
    """Each contact in stakeholder_map.stakeholders gets a dedicated slide."""
    stakeholder_map = {
        "stakeholders": [
            {
                "name": "Alice Chen",
                "title": "Chief Technology Officer",
                "csuiteCategory": "CTO",
                "email": "alice@acme.com",
                "linkedin": "https://linkedin.com/in/alicechen",
            },
            {
                "name": "Bob Rivera",
                "title": "VP Engineering",
                "csuiteCategory": "CTO",
                "email": "bob@acme.com",
                "linkedin": "https://linkedin.com/in/bobrivera",
            },
            {
                "name": "Carol Park",
                "title": "Chief Financial Officer",
                "csuiteCategory": "CFO",
                "email": "carol@acme.com",
                "linkedin": "https://linkedin.com/in/carolpark",
            },
        ],
        "otherContacts": [],
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(stakeholder_map=stakeholder_map)
    )

    # Each contact should appear with their own slide heading
    assert "Alice Chen" in markdown
    assert "Bob Rivera" in markdown
    assert "Carol Park" in markdown

    # Each should have a dedicated slide title with their name
    assert "# Alice Chen" in markdown
    assert "# Bob Rivera" in markdown
    assert "# Carol Park" in markdown


def test_csuite_category_shown_on_slide():
    """The csuiteCategory label should appear on each stakeholder's slide."""
    stakeholder_map = {
        "stakeholders": [
            {
                "name": "Dan Lee",
                "title": "Chief Information Officer",
                "csuiteCategory": "CIO",
                "email": "dan@acme.com",
                "linkedin": "https://linkedin.com/in/danlee",
            },
            {
                "name": "Eve Walsh",
                "title": "Director of IT",
                "csuiteCategory": "CIO",
                "email": "eve@acme.com",
                "linkedin": "https://linkedin.com/in/evewalsh",
            },
        ],
        "otherContacts": [],
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(stakeholder_map=stakeholder_map)
    )

    # Both should show CIO category
    assert "Dan Lee – CIO" in markdown
    assert "Eve Walsh – CIO" in markdown


def test_multiple_contacts_per_category_each_get_slide():
    """If CTO has 3 contacts, all 3 get individual slides (not grouped into one)."""
    stakeholder_map = {
        "stakeholders": [
            {"name": "Person A", "title": "CTO", "csuiteCategory": "CTO",
             "email": "a@co.com", "linkedin": "https://linkedin.com/in/a"},
            {"name": "Person B", "title": "VP Platform", "csuiteCategory": "CTO",
             "email": "b@co.com", "linkedin": "https://linkedin.com/in/b"},
            {"name": "Person C", "title": "Head of Engineering", "csuiteCategory": "CTO",
             "email": "c@co.com", "linkedin": "https://linkedin.com/in/c"},
        ],
        "otherContacts": [],
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(stakeholder_map=stakeholder_map)
    )

    # Count slide separators (---) after stakeholder sections
    # Each stakeholder slide ends with ---
    # Should have 3 individual stakeholder profile headings
    assert "# Person A – CTO" in markdown
    assert "# Person B – CTO" in markdown
    assert "# Person C – CTO" in markdown


def test_stakeholder_map_preferred_over_profiles():
    """stakeholder_map.stakeholders is used instead of stakeholder_profiles."""
    stakeholder_map = {
        "stakeholders": [
            {"name": "Map Contact", "title": "CTO", "csuiteCategory": "CTO",
             "email": "map@co.com", "linkedin": "https://linkedin.com/in/map"},
        ],
        "otherContacts": [],
    }
    profiles = [
        {"name": "Profile Contact", "title": "CTO",
         "email": "profile@co.com", "linkedin": "https://linkedin.com/in/profile"},
    ]

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(
            stakeholder_map=stakeholder_map,
            stakeholder_profiles=profiles,
        )
    )

    assert "Map Contact" in markdown
    assert "Profile Contact" not in markdown


def test_fallback_to_stakeholder_profiles_when_no_map():
    """Falls back to stakeholder_profiles when stakeholder_map is absent."""
    profiles = [
        {"name": "Legacy Contact", "title": "Chief Financial Officer",
         "email": "legacy@co.com", "linkedin": "https://linkedin.com/in/legacy"},
    ]

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(stakeholder_profiles=profiles)
    )

    assert "Legacy Contact" in markdown


def test_contact_details_on_individual_slide():
    """Each slide includes full contact details: email, phone, LinkedIn, bio."""
    stakeholder_map = {
        "stakeholders": [
            {
                "name": "Full Contact",
                "title": "Chief Technology Officer",
                "csuiteCategory": "CTO",
                "email": "full@acme.com",
                "direct_phone": "+1-555-0100",
                "mobile": "+1-555-0101",
                "linkedin": "https://linkedin.com/in/fullcontact",
                "bio": "Seasoned technology leader with 20 years experience.",
                "strategic_priorities": [
                    {"name": "Cloud Migration", "description": "Moving to hybrid cloud."},
                    {"name": "AI Adoption", "description": "Enterprise AI strategy."},
                ],
                "communication_preference": "Email and LinkedIn",
                "conversation_starters": ["Recent cloud investments", "AI roadmap"],
            },
        ],
        "otherContacts": [],
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=_make_company_data(stakeholder_map=stakeholder_map)
    )

    assert "full@acme.com" in markdown
    assert "+1-555-0100" in markdown
    assert "+1-555-0101" in markdown
    assert "linkedin.com/in/fullcontact" in markdown
    assert "Seasoned technology leader" in markdown
    assert "Cloud Migration" in markdown
    assert "AI Adoption" in markdown
    # Communication preference is now computed from available channels in
    # Phone / Email / LinkedIn order; the LLM-supplied free-text value is
    # no longer rendered. This stakeholder has phone + email + linkedin,
    # so all three channels must appear in the comm-pref line.
    assert "Phone / Email / LinkedIn" in markdown
