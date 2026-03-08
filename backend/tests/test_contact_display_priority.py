"""
Tests for contact display priority: data completeness as secondary sort layer.
TDD: Tests written FIRST before implementation.

Rules:
1. Role type still determines primary (CTO/CIO/CFO/CMO) vs otherContacts
2. Within each group, contacts sorted by data completeness:
   Tier 1: Has LinkedIn + phone + email (all three)
   Tier 2: ZoomInfo source (best data provider)
   Tier 3: Missing phone (has LinkedIn + email only)
   Tier 4: Other (least complete)
3. Role priority (CTO > CIO > CFO > CMO etc.) is tiebreaker within same tier
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_contact(name, role_type, email=None, phone=None, linkedin_url=None, source=None):
    """Helper to build a contact dict."""
    return {
        "name": name,
        "title": f"Chief {role_type} Officer",
        "role_type": role_type,
        "email": email,
        "phone": phone,
        "linkedin_url": linkedin_url,
        "source": source or "apollo",
    }


class TestContactDataCompletenessTier:
    """Test the _contact_data_tier function returns correct tier."""

    def test_all_three_fields_is_tier_0(self):
        """Contact with LinkedIn + phone + email = tier 0 (highest)."""
        from production_main import _contact_data_tier
        c = _make_contact("A", "CTO", email="a@x.com", phone="+1-555", linkedin_url="https://linkedin.com/in/a")
        assert _contact_data_tier(c) == 0

    def test_zoominfo_source_is_tier_1(self):
        """ZoomInfo contact without all three fields = tier 1."""
        from production_main import _contact_data_tier
        c = _make_contact("B", "CIO", email="b@x.com", phone="+1-555", source="zoominfo")
        assert _contact_data_tier(c) == 1

    def test_zoominfo_with_all_three_is_tier_0_not_1(self):
        """ZoomInfo contact WITH all three fields = tier 0 (completeness beats source)."""
        from production_main import _contact_data_tier
        c = _make_contact("C", "CFO", email="c@x.com", phone="+1-555", linkedin_url="https://linkedin.com/in/c", source="zoominfo")
        assert _contact_data_tier(c) == 0

    def test_missing_phone_is_tier_2(self):
        """Contact with LinkedIn + email but no phone = tier 2."""
        from production_main import _contact_data_tier
        c = _make_contact("D", "CTO", email="d@x.com", linkedin_url="https://linkedin.com/in/d")
        assert _contact_data_tier(c) == 2

    def test_other_incomplete_is_tier_3(self):
        """Contact missing multiple fields = tier 3."""
        from production_main import _contact_data_tier
        c = _make_contact("E", "VP", email="e@x.com")
        assert _contact_data_tier(c) == 3

    def test_only_linkedin_no_phone_no_email_is_tier_3(self):
        """Contact with only LinkedIn = tier 3."""
        from production_main import _contact_data_tier
        c = _make_contact("F", "Director", linkedin_url="https://linkedin.com/in/f")
        assert _contact_data_tier(c) == 3

    def test_phone_and_email_no_linkedin_zoominfo_is_tier_1(self):
        """ZoomInfo contact with phone+email but no LinkedIn = tier 1 (ZoomInfo source)."""
        from production_main import _contact_data_tier
        c = _make_contact("G", "CTO", email="g@x.com", phone="+1-555", source="zoominfo")
        assert _contact_data_tier(c) == 1


class TestStakeholderSortWithDataCompleteness:
    """Test that within primary/other groups, data completeness sorts contacts."""

    def test_primary_sorted_by_completeness_then_role(self):
        """Within primary stakeholders, all-three-fields contacts come first."""
        from production_main import _contact_data_tier, ROLE_PRIORITY, PRIMARY_STAKEHOLDER_ROLES

        contacts = [
            _make_contact("CTO NoPhone", "CTO", email="a@x.com", linkedin_url="https://li.com/a"),
            _make_contact("CIO Complete", "CIO", email="b@x.com", phone="+1", linkedin_url="https://li.com/b"),
            _make_contact("CFO Complete", "CFO", email="c@x.com", phone="+1", linkedin_url="https://li.com/c"),
        ]

        # All are primary roles — sort by data tier then role priority
        primary = [c for c in contacts if c["role_type"] in PRIMARY_STAKEHOLDER_ROLES]
        primary.sort(key=lambda x: (
            _contact_data_tier(x),
            ROLE_PRIORITY.get(x["role_type"].lower(), 99),
        ))

        names = [c["name"] for c in primary]
        # CIO Complete and CFO Complete (tier 0) before CTO NoPhone (tier 2)
        assert names.index("CIO Complete") < names.index("CTO NoPhone")
        assert names.index("CFO Complete") < names.index("CTO NoPhone")

    def test_other_contacts_sorted_by_completeness(self):
        """otherContacts also sorted by data completeness."""
        from production_main import _contact_data_tier, ROLE_PRIORITY

        contacts = [
            _make_contact("VP Bare", "VP", email="v@x.com"),
            _make_contact("CEO Full", "CEO", email="c@x.com", phone="+1", linkedin_url="https://li.com/c"),
            _make_contact("CISO ZI", "CISO", email="s@x.com", phone="+1", source="zoominfo"),
        ]

        contacts.sort(key=lambda x: (
            _contact_data_tier(x),
            ROLE_PRIORITY.get(x["role_type"].lower(), 99),
        ))

        names = [c["name"] for c in contacts]
        # CEO Full (tier 0) first, CISO ZI (tier 1) second, VP Bare (tier 3) last
        assert names[0] == "CEO Full"
        assert names[1] == "CISO ZI"
        assert names[2] == "VP Bare"

    def test_fallback_promotion_uses_data_completeness(self):
        """When no primary roles, fallback promotes most complete contacts."""
        from production_main import _contact_data_tier, ROLE_PRIORITY

        contacts = [
            _make_contact("VP Bare", "VP", email="v@x.com"),
            _make_contact("CEO Full", "CEO", email="c@x.com", phone="+1", linkedin_url="https://li.com/c"),
            _make_contact("CISO ZI", "CISO", email="s@x.com", phone="+1", source="zoominfo"),
            _make_contact("Dir Full", "Director", email="d@x.com", phone="+1", linkedin_url="https://li.com/d"),
            _make_contact("Mgr Bare", "Manager", email="m@x.com"),
        ]

        # Simulate fallback sort
        contacts.sort(key=lambda x: (
            _contact_data_tier(x),
            ROLE_PRIORITY.get(x["role_type"].lower(), 99),
        ))

        promoted = contacts[:4]
        promoted_names = [c["name"] for c in promoted]
        # CEO Full and Dir Full (tier 0) should be promoted first
        assert "CEO Full" in promoted_names
        assert "Dir Full" in promoted_names
        # CISO ZI (tier 1) promoted before tier-3 contacts
        assert "CISO ZI" in promoted_names
        # Mgr Bare (tier 3, worst role priority) should be last
        assert contacts[-1]["name"] == "Mgr Bare"

    def test_same_tier_uses_role_priority_as_tiebreaker(self):
        """Within the same data tier, role priority (CTO > CIO > CFO) breaks ties."""
        from production_main import _contact_data_tier, ROLE_PRIORITY

        contacts = [
            _make_contact("CFO Full", "CFO", email="a@x.com", phone="+1", linkedin_url="https://li.com/a"),
            _make_contact("CTO Full", "CTO", email="b@x.com", phone="+1", linkedin_url="https://li.com/b"),
            _make_contact("CIO Full", "CIO", email="c@x.com", phone="+1", linkedin_url="https://li.com/c"),
        ]

        contacts.sort(key=lambda x: (
            _contact_data_tier(x),
            ROLE_PRIORITY.get(x["role_type"].lower(), 99),
        ))

        names = [c["name"] for c in contacts]
        assert names == ["CTO Full", "CIO Full", "CFO Full"]
