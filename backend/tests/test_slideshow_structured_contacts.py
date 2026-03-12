"""
Tests for structured stakeholder slides in Gamma slideshow.
TDD: Tests written FIRST.

Verifies:
1. Executive stakeholders appear under their C-suite category
2. Relevant other contacts (sales, partnerships, strategy, communications) get slides
3. Non-relevant other contacts are excluded
4. Phone numbers are displayed when available
5. Each contact gets their own slide
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


def test_executives_and_relevant_contacts_together():
    """Both executives and relevant other contacts appear, each on own slide."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {"name": "Alice CTO", "title": "CTO", "csuiteCategory": "CTO"},
    ]
    other_contacts = [
        {"name": "Bob Sales", "title": "VP Sales"},
        {"name": "Charlie Dev", "title": "Senior Developer"},  # excluded
    ]
    data = _make_company_data(stakeholders, other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    md = creator._generate_markdown(data)

    assert "Alice CTO" in md
    assert "Bob Sales" in md
    assert "Charlie Dev" not in md


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

    # Should show title-based label, not "Executive Stakeholder Profile"
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


def test_template_data_includes_all_executive_stakeholders():
    """_format_for_template must include EVERY executive from stakeholder_map.stakeholders."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {"name": "Alice CEO", "title": "Chief Executive Officer", "csuiteCategory": "CEO"},
        {"name": "Bob CTO", "title": "Chief Technology Officer", "csuiteCategory": "CTO"},
        {"name": "Carol CFO", "title": "Chief Financial Officer", "csuiteCategory": "CFO"},
        {"name": "Dave CIO", "title": "Chief Information Officer", "csuiteCategory": "CIO"},
        {"name": "Eve CMO", "title": "Chief Marketing Officer", "csuiteCategory": "CMO"},
    ]
    data = _make_company_data(stakeholders, [])
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    for s in stakeholders:
        assert s["name"] in template_data, f"{s['name']} missing from template data"


def test_template_data_includes_relevant_other_contacts():
    """_format_for_template must include sales/partnerships/strategy/comms contacts."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    other_contacts = [
        {"name": "Dan Sales", "title": "VP of Sales"},
        {"name": "Eve Partner", "title": "Director of Partnerships"},
        {"name": "Frank Strategy", "title": "Head of Strategy"},
        {"name": "Grace Comms", "title": "VP Communications"},
    ]
    data = _make_company_data([], other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    for c in other_contacts:
        assert c["name"] in template_data, f"{c['name']} missing from template data"


def test_template_data_excludes_irrelevant_contacts():
    """_format_for_template must NOT include engineers, analysts, etc."""
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


def test_template_data_shows_phone_numbers():
    """_format_for_template must show phone numbers for contacts that have them."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {
            "name": "Jane Doe",
            "title": "CTO",
            "csuiteCategory": "CTO",
            "direct_phone": "+1-555-0001",
            "mobile_phone": "+1-555-0002",
        },
    ]
    other_contacts = [
        {
            "name": "Dan Sales",
            "title": "VP of Sales",
            "direct_phone": "+1-555-9999",
        },
    ]
    data = _make_company_data(stakeholders, other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    assert "+1-555-0001" in template_data, "Executive direct phone should appear"
    assert "+1-555-0002" in template_data, "Executive mobile phone should appear"
    assert "+1-555-9999" in template_data, "Other contact phone should appear"


def test_template_data_each_stakeholder_gets_own_section():
    """Each stakeholder in _format_for_template should have a clearly separated section."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    stakeholders = [
        {"name": "Alice CEO", "title": "CEO", "csuiteCategory": "CEO"},
        {"name": "Bob CTO", "title": "CTO", "csuiteCategory": "CTO"},
    ]
    other_contacts = [
        {"name": "Dan Sales", "title": "VP Sales"},
    ]
    data = _make_company_data(stakeholders, other_contacts)
    creator = GammaSlideshowCreator(gamma_api_key="test")
    template_data = creator._format_for_template(data)

    # Each contact should appear as a separate stakeholder section
    assert "Alice CEO" in template_data
    assert "Bob CTO" in template_data
    assert "Dan Sales" in template_data
    # Each should have title shown
    assert "CEO" in template_data
    assert "CTO" in template_data
    assert "VP Sales" in template_data
