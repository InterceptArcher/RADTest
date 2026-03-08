"""
Tests for C-suite affiliation mapping: lax title matching to C-suite categories.
TDD: Tests written FIRST before implementation.

Rules:
1. Direct C-suite titles map to themselves (CTO title -> CTO category)
2. People working in the "office of" a C-suite exec map to that exec's category
3. Senior reports / functional heads map to the relevant C-suite category
4. Max 3 contacts per C-suite category, picked by data completeness
5. Contacts that don't affiliate with any PRIMARY C-suite go to otherContacts
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCsuiteAffiliation:
    """Test _csuite_affiliation returns the correct C-suite category."""

    def test_direct_cto_title(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief Technology Officer") == "CTO"

    def test_direct_cio_title(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief Information Officer") == "CIO"

    def test_direct_cfo_title(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief Financial Officer") == "CFO"

    def test_direct_cmo_title(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief Marketing Officer") == "CMO"

    def test_office_of_ceo(self):
        """'Office of the Chief Executive Officer' affiliates with CEO."""
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Senior Manager, Executive Communications, Office of the Chief Executive Officer") == "CEO"

    def test_office_of_cto(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Director, Office of the CTO") == "CTO"

    def test_office_of_cfo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Executive Assistant, Office of the CFO") == "CFO"

    def test_vp_engineering_affiliates_cto(self):
        """VP of Engineering is a CTO-adjacent role."""
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP of Engineering") == "CTO"

    def test_vp_technology_affiliates_cto(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Vice President, Technology") == "CTO"

    def test_senior_director_engineering_affiliates_cto(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Senior Director of Engineering") == "CTO"

    def test_head_of_it_affiliates_cio(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Head of IT Infrastructure") == "CIO"

    def test_vp_information_systems_affiliates_cio(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP Information Systems") == "CIO"

    def test_it_director_affiliates_cio(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("IT Director") == "CIO"

    def test_vp_finance_affiliates_cfo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP of Finance") == "CFO"

    def test_controller_affiliates_cfo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Corporate Controller") == "CFO"

    def test_director_financial_planning_affiliates_cfo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Director of Financial Planning & Analysis") == "CFO"

    def test_vp_marketing_affiliates_cmo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP of Marketing") == "CMO"

    def test_director_digital_marketing_affiliates_cmo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Director, Digital Marketing") == "CMO"

    def test_head_of_brand_affiliates_cmo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Head of Brand Strategy") == "CMO"

    def test_vp_security_affiliates_ciso(self):
        """CISO-adjacent roles affiliate with CISO (not primary, but still mapped)."""
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP of Cybersecurity") == "CISO"

    def test_ceo_direct(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief Executive Officer") == "CEO"

    def test_president_affiliates_ceo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("President and Co-Founder") == "CEO"

    def test_chief_of_staff_affiliates_ceo(self):
        """Chief of Staff typically reports directly to CEO."""
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Chief of Staff") == "CEO"

    def test_unrelated_title_returns_none(self):
        """Titles with no clear C-suite affiliation return None."""
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Account Executive") is None

    def test_empty_title_returns_none(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("") is None

    def test_generic_manager_returns_none(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Regional Sales Manager") is None

    def test_senior_director_software_affiliates_cto(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Senior Director, Software Development") == "CTO"

    def test_treasurer_affiliates_cfo(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("Treasurer") == "CFO"

    def test_vp_data_affiliates_cio(self):
        from production_main import _csuite_affiliation
        assert _csuite_affiliation("VP of Data & Analytics") == "CIO"


class TestStakeholderGrouping:
    """Test that stakeholders are grouped by C-suite category with max 3 per group."""

    def _make_contact(self, name, title, role_type, email=None, phone=None, linkedin_url=None, source=None):
        return {
            "name": name,
            "title": title,
            "role_type": role_type,
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "source": source or "apollo",
        }

    def test_max_3_per_csuite_category(self):
        """No more than 3 contacts per C-suite category in stakeholders."""
        from production_main import _csuite_affiliation, _contact_data_tier, ROLE_PRIORITY, PRIMARY_STAKEHOLDER_ROLES, _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO Person", "Chief Technology Officer", "CTO", "a@x.com", "+1", "https://li.com/a", "zoominfo"),
            self._make_contact("VP Eng 1", "VP of Engineering", "VP", "b@x.com", "+1", "https://li.com/b"),
            self._make_contact("VP Eng 2", "VP Engineering", "VP", "c@x.com", "+1", "https://li.com/c"),
            self._make_contact("Dir Eng", "Director of Engineering", "Director", "d@x.com", "+1", "https://li.com/d"),
            self._make_contact("Sr Dir Eng", "Senior Director, Software", "Director", "e@x.com", "+1", "https://li.com/e"),
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        cto_group = [c for c in primary if c.get("csuiteCategory") == "CTO"]
        assert len(cto_group) <= 3

    def test_data_completeness_determines_selection(self):
        """Within a category, most data-complete contacts are selected."""
        from production_main import _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO", "Chief Technology Officer", "CTO", "a@x.com"),  # tier 3 - only email
            self._make_contact("VP Eng Full", "VP of Engineering", "VP", "b@x.com", "+1", "https://li.com/b"),  # tier 0
            self._make_contact("Dir Eng Full", "Director Engineering", "Director", "c@x.com", "+1", "https://li.com/c"),  # tier 0
            self._make_contact("Sr Dir Full", "Senior Director, Software Development", "Director", "d@x.com", "+1", "https://li.com/d"),  # tier 0
            self._make_contact("Mgr Eng Bare", "Engineering Manager", "Manager", "e@x.com"),  # tier 3
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        cto_names = [c["name"] for c in primary if c.get("csuiteCategory") == "CTO"]
        # The 3 with full data should be selected over the CTO with only email
        assert "VP Eng Full" in cto_names
        assert "Dir Eng Full" in cto_names
        assert "Sr Dir Full" in cto_names

    def test_non_affiliated_go_to_other(self):
        """Contacts with no C-suite affiliation go to other list."""
        from production_main import _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO", "Chief Technology Officer", "CTO", "a@x.com", "+1", "https://li.com/a"),
            self._make_contact("Sales Rep", "Account Executive", "Unknown", "b@x.com"),
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        other_names = [c["name"] for c in other]
        assert "Sales Rep" in other_names

    def test_multiple_categories_each_get_3(self):
        """CTO and CFO categories each get up to 3 contacts."""
        from production_main import _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO", "Chief Technology Officer", "CTO", "a@x.com", "+1", "https://li.com/a"),
            self._make_contact("VP Eng", "VP Engineering", "VP", "b@x.com", "+1", "https://li.com/b"),
            self._make_contact("CFO", "Chief Financial Officer", "CFO", "c@x.com", "+1", "https://li.com/c"),
            self._make_contact("VP Fin", "VP of Finance", "VP", "d@x.com", "+1", "https://li.com/d"),
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        cto_group = [c for c in primary if c.get("csuiteCategory") == "CTO"]
        cfo_group = [c for c in primary if c.get("csuiteCategory") == "CFO"]
        assert len(cto_group) == 2
        assert len(cfo_group) == 2

    def test_excess_contacts_overflow_to_other(self):
        """4th+ contact in a category goes to otherContacts."""
        from production_main import _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO", "CTO", "CTO", "a@x.com", "+1", "https://li.com/a"),
            self._make_contact("VP1", "VP Engineering", "VP", "b@x.com", "+1", "https://li.com/b"),
            self._make_contact("VP2", "VP Technology", "VP", "c@x.com", "+1", "https://li.com/c"),
            self._make_contact("Dir1", "Director Engineering", "Director", "d@x.com", "+1", "https://li.com/d"),
            self._make_contact("Dir2", "Director Software", "Director", "e@x.com", "+1", "https://li.com/e"),
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        cto_group = [c for c in primary if c.get("csuiteCategory") == "CTO"]
        assert len(cto_group) == 3
        # Overflow contacts should be in other
        overflow_names = [c["name"] for c in other]
        assert len(overflow_names) >= 2

    def test_primary_contacts_have_csuite_category_field(self):
        """Each primary contact has a csuiteCategory field set."""
        from production_main import _group_stakeholders_by_csuite

        contacts = [
            self._make_contact("CTO", "Chief Technology Officer", "CTO", "a@x.com", "+1", "https://li.com/a"),
        ]

        primary, other = _group_stakeholders_by_csuite(contacts)
        assert all(c.get("csuiteCategory") for c in primary)
