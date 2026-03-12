"""
Tests for structured stakeholder slides in Gamma slideshow.
TDD: Tests written FIRST.

Verifies:
1. One BEST contact per C-suite role in template data (quality-ranked)
2. Relevant other contacts (sales, partnerships, strategy, communications) included
3. Non-relevant other contacts are excluded
4. Phone numbers are displayed when available
5. Quality ranking: linkedin+phone+email > partial data > no data
6. Title quality: actual C-suite title beats VP/Director for same role
"""
import pytest


def _make_company_data(stakeholders, other_contacts):
    """Helper to build company_data with stakeholder_map."""
    return {
        "company_name": "Acme Corp",
        "validated_data": {
            "company_name": "Acme Corp",
            "industry": "Technology",
            "employee_count": 500,
            "stakeholder_map": {
                "stakeholders": stakeholders,
                "otherContacts": other_contacts,
            },
        },
        "confidence_score": 0.85,
    }


# ── _generate_markdown tests (standard endpoint) ──


def test_executive_stakeholders_get_slides():
    """All executive stakeholders from stakeholder_map.stakeholders get slides."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {"name": "Alice CEO", "title": "Chief Executive Officer", "csuiteCategory": "CEO"},
        {"name": "Bob CTO", "title": "Chief Technology Officer", "csuiteCategory": "CTO"},
        {"name": "Carol CFO", "title": "Chief Financial Officer", "csuiteCategory": "CFO"},
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Alice CEO" in md
    assert "Bob CTO" in md
    assert "Carol CFO" in md
    assert "CEO Stakeholder Profile" in md
    assert "CTO Stakeholder Profile" in md
    assert "CFO Stakeholder Profile" in md


def test_relevant_other_contacts_get_slides():
    """Contacts in sales/partnerships/strategy/communications get slides."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Dan Sales", "title": "VP of Sales"},
        {"name": "Eve Partner", "title": "Director of Partnerships"},
        {"name": "Frank Strategy", "title": "Head of Strategy"},
        {"name": "Grace Comms", "title": "VP Communications"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Dan Sales" in md
    assert "Eve Partner" in md
    assert "Frank Strategy" in md
    assert "Grace Comms" in md


def test_irrelevant_other_contacts_excluded():
    """Contacts NOT in sales/partnerships/strategy/communications are excluded."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Included", "title": "VP of Sales"},
        {"name": "Excluded Engineer", "title": "Senior Software Engineer"},
        {"name": "Excluded Analyst", "title": "Financial Analyst"},
        {"name": "Excluded Admin", "title": "Office Administrator"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Included" in md
    assert "Excluded Engineer" not in md
    assert "Excluded Analyst" not in md
    assert "Excluded Admin" not in md


def test_phone_numbers_displayed():
    """Contacts with phone numbers should have them in the slideshow."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {
            "name": "Jane Doe",
            "title": "CTO",
            "csuiteCategory": "CTO",
            "direct_phone": "+1-555-0001",
            "mobile_phone": "+1-555-0002",
            "company_phone": "+1-555-0003",
            "contact": {
                "email": "jane@acme.com",
                "directPhone": "+1-555-0001",
                "mobilePhone": "+1-555-0002",
                "companyPhone": "+1-555-0003",
            },
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "+1-555-0001" in md, "Direct phone should appear"
    assert "+1-555-0002" in md, "Mobile phone should appear"
    assert "+1-555-0003" in md, "Company phone should appear"


def test_relevant_contact_slide_shows_title():
    """Relevant other contacts show their actual title, not a C-suite category."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Dan Sales", "title": "VP of Sales"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "VP of Sales" in md


def test_business_development_role_included():
    """Business development contacts should be included as relevant."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "BD Person", "title": "Director of Business Development"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "BD Person" in md


def test_channel_alliances_role_included():
    """Channel/alliances contacts should be included."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Channel Person", "title": "Channel Sales Manager"},
        {"name": "Alliance Person", "title": "VP Strategic Alliances"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Channel Person" in md
    assert "Alliance Person" in md


def test_other_contact_phone_in_generate_markdown():
    """Other relevant contacts' phones must appear in _generate_markdown output."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {
            "name": "Dan Sales",
            "title": "VP of Sales",
            "direct_phone": "+1-555-7777",
            "contact": {"directPhone": "+1-555-7777", "email": "dan@acme.com"},
        },
        {
            "name": "Eve Partner",
            "title": "Director of Partnerships",
            "mobile_phone": "+1-555-8888",
            "contact": {"mobilePhone": "+1-555-8888"},
        },
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Dan Sales" in md
    assert "+1-555-7777" in md, "Sales VP direct phone missing from markdown"
    assert "Eve Partner" in md
    assert "+1-555-8888" in md, "Partnerships director mobile phone missing from markdown"


# ── _format_for_template tests (template endpoint: 1 best per role) ──


def test_template_picks_one_best_contact_per_csuite_role():
    """When multiple contacts share a csuiteCategory, pick the one with best data."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        # CTO #1: has linkedin + phone + email — best quality
        {
            "name": "Best CTO",
            "title": "Chief Technology Officer",
            "csuiteCategory": "CTO",
            "email": "best@acme.com",
            "direct_phone": "+1-555-1111",
            "linkedin_url": "https://linkedin.com/in/bestcto",
            "contact": {
                "email": "best@acme.com",
                "directPhone": "+1-555-1111",
                "linkedinUrl": "https://linkedin.com/in/bestcto",
            },
        },
        # CTO #2: only has email — lower quality
        {
            "name": "Worse CTO",
            "title": "VP Engineering",
            "csuiteCategory": "CTO",
            "email": "worse@acme.com",
            "contact": {"email": "worse@acme.com"},
        },
        # CTO #3: no contact info
        {
            "name": "Worst CTO",
            "title": "Director of Engineering",
            "csuiteCategory": "CTO",
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Best CTO" in template_data
    assert "Worse CTO" not in template_data
    assert "Worst CTO" not in template_data


def test_template_one_per_role_across_categories():
    """Each C-suite category gets exactly 1 contact in template data."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {"name": "CEO Person", "title": "CEO", "csuiteCategory": "CEO",
         "email": "ceo@acme.com", "linkedin_url": "https://linkedin.com/in/ceo",
         "contact": {"email": "ceo@acme.com", "linkedinUrl": "https://linkedin.com/in/ceo"}},
        {"name": "CTO Person", "title": "CTO", "csuiteCategory": "CTO",
         "email": "cto@acme.com", "direct_phone": "+1-555-0001",
         "contact": {"email": "cto@acme.com", "directPhone": "+1-555-0001"}},
        {"name": "CFO Person", "title": "CFO", "csuiteCategory": "CFO",
         "email": "cfo@acme.com",
         "contact": {"email": "cfo@acme.com"}},
        # Second CTO — should be excluded
        {"name": "Extra CTO", "title": "VP Technology", "csuiteCategory": "CTO",
         "contact": {}},
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "CEO Person" in template_data
    assert "CTO Person" in template_data
    assert "CFO Person" in template_data
    assert "Extra CTO" not in template_data


def test_template_prefers_contact_with_all_three_fields():
    """Contact with linkedin+phone+email beats one with only email."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        # CFO with only email
        {
            "name": "Email Only CFO",
            "title": "Chief Financial Officer",
            "csuiteCategory": "CFO",
            "email": "cfo@acme.com",
            "contact": {"email": "cfo@acme.com"},
        },
        # CFO with all 3
        {
            "name": "Complete CFO",
            "title": "CFO",
            "csuiteCategory": "CFO",
            "email": "complete@acme.com",
            "direct_phone": "+1-555-3333",
            "linkedin_url": "https://linkedin.com/in/completecfo",
            "contact": {
                "email": "complete@acme.com",
                "directPhone": "+1-555-3333",
                "linkedinUrl": "https://linkedin.com/in/completecfo",
            },
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Complete CFO" in template_data
    assert "Email Only CFO" not in template_data


def test_template_shows_phone_for_best_contact():
    """The best contact's phone numbers must appear in template data."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {
            "name": "Jane CTO",
            "title": "CTO",
            "csuiteCategory": "CTO",
            "direct_phone": "+1-555-0001",
            "mobile_phone": "+1-555-0002",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/janecto",
            "contact": {
                "email": "jane@acme.com",
                "directPhone": "+1-555-0001",
                "mobilePhone": "+1-555-0002",
                "linkedinUrl": "https://linkedin.com/in/janecto",
            },
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "+1-555-0001" in template_data, "Direct phone should appear"
    assert "+1-555-0002" in template_data, "Mobile phone should appear"


def test_template_includes_relevant_other_contacts():
    """Template should still include relevant other contacts (sales/partnerships/etc)."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Dan Sales", "title": "VP of Sales",
         "direct_phone": "+1-555-9999",
         "contact": {"directPhone": "+1-555-9999", "email": "dan@acme.com"}},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Dan Sales" in template_data
    assert "+1-555-9999" in template_data, "Other contact phone should appear"


def test_template_excludes_irrelevant_other_contacts():
    """Template must NOT include engineers, analysts, etc from otherContacts."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Included VP Sales", "title": "VP of Sales"},
        {"name": "Excluded Engineer", "title": "Senior Software Engineer"},
        {"name": "Excluded Analyst", "title": "Financial Analyst"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Included VP Sales" in template_data
    assert "Excluded Engineer" not in template_data
    assert "Excluded Analyst" not in template_data


def test_template_prefers_true_csuite_title_over_vp():
    """When two contacts share a category, prefer the one whose title is
    more senior / more directly C-suite (better for sales outreach)."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        # VP Engineering — has all contact data but weaker title
        {
            "name": "VP Eng",
            "title": "VP of Engineering",
            "csuiteCategory": "CTO",
            "email": "vp@acme.com",
            "direct_phone": "+1-555-1111",
            "linkedin_url": "https://linkedin.com/in/vpeng",
            "contact": {
                "email": "vp@acme.com",
                "directPhone": "+1-555-1111",
                "linkedinUrl": "https://linkedin.com/in/vpeng",
            },
        },
        # Actual CTO — also has all contact data, stronger title
        {
            "name": "Actual CTO",
            "title": "Chief Technology Officer",
            "csuiteCategory": "CTO",
            "email": "cto@acme.com",
            "direct_phone": "+1-555-2222",
            "linkedin_url": "https://linkedin.com/in/actualcto",
            "contact": {
                "email": "cto@acme.com",
                "directPhone": "+1-555-2222",
                "linkedinUrl": "https://linkedin.com/in/actualcto",
            },
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Actual CTO" in template_data
    assert "VP Eng" not in template_data


def test_template_fallback_dict_stakeholder_profiles():
    """When stakeholder_map is empty, _format_for_template should fall back to
    stakeholder_profiles as a dict (keyed by role type) from the LLM council."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    data = {
        "company_name": "Acme Corp",
        "validated_data": {
            "company_name": "Acme Corp",
            "industry": "Technology",
            "employee_count": 500,
            "stakeholder_map": {},  # empty — no contacts from APIs
            "stakeholder_profiles": {
                "CTO": {
                    "name": "Jane CTO",
                    "title": "Chief Technology Officer",
                    "bio": "Leads technology strategy",
                    "strategic_priorities": ["Cloud migration", "AI adoption"],
                },
                "CFO": {
                    "name": "Bob CFO",
                    "title": "Chief Financial Officer",
                    "bio": "Oversees financial operations",
                },
            },
        },
        "confidence_score": 0.85,
    }
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Jane CTO" in template_data, "Dict stakeholder_profiles CTO should appear"
    assert "Bob CFO" in template_data, "Dict stakeholder_profiles CFO should appear"


def test_template_exact_role_match_beats_generic_csuite():
    """A contact whose title exactly matches the C-suite category should be
    preferred over one with a generic C-suite title but different role."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        # CEO who was somehow bucketed into CTO category — wrong match
        {
            "name": "Wrong CEO",
            "title": "Chief Executive Officer",
            "csuiteCategory": "CTO",
            "email": "ceo@acme.com",
            "direct_phone": "+1-555-1111",
            "linkedin_url": "https://linkedin.com/in/ceo",
            "contact": {
                "email": "ceo@acme.com",
                "directPhone": "+1-555-1111",
                "linkedinUrl": "https://linkedin.com/in/ceo",
            },
        },
        # Actual CTO — exact role match for CTO category
        {
            "name": "Right CTO",
            "title": "Chief Technology Officer",
            "csuiteCategory": "CTO",
            "email": "cto@acme.com",
            "direct_phone": "+1-555-2222",
            "linkedin_url": "https://linkedin.com/in/cto",
            "contact": {
                "email": "cto@acme.com",
                "directPhone": "+1-555-2222",
                "linkedinUrl": "https://linkedin.com/in/cto",
            },
        },
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "Right CTO" in template_data, "Exact CTO title should win CTO slot"
    assert "Wrong CEO" not in template_data, "CEO title should not take CTO slot"
