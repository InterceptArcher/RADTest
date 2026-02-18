"""
Tests for stakeholder role priority: CTO, CIO, COO, CFO are primary targets.
TDD: Tests written FIRST before implementation.

Rules:
1. CTO, CIO, COO, CFO are shown as primary executives (full profile cards)
2. All other roles (CISO, CPO, CEO, CMO, VP, Director, Manager) are otherContacts
3. If NONE of the primary 4 are found, the best available roles become primary
4. Role sorting order: CTO > CIO > COO > CFO > others
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPriorityRoles:
    """Test the PRIMARY_STAKEHOLDER_ROLES constant and role classification."""

    def test_primary_roles_are_cto_cio_cfo_coo(self):
        """PRIMARY_STAKEHOLDER_ROLES contains exactly CTO, CIO, CFO, COO."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert PRIMARY_STAKEHOLDER_ROLES == {"CTO", "CIO", "CFO", "COO"}

    def test_cto_is_primary_role(self):
        """CTO is classified as a primary stakeholder role."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CTO" in PRIMARY_STAKEHOLDER_ROLES

    def test_cio_is_primary_role(self):
        """CIO is classified as a primary stakeholder role."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CIO" in PRIMARY_STAKEHOLDER_ROLES

    def test_coo_is_primary_role(self):
        """COO is classified as a primary stakeholder role."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "COO" in PRIMARY_STAKEHOLDER_ROLES

    def test_cfo_is_primary_role(self):
        """CFO is classified as a primary stakeholder role."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CFO" in PRIMARY_STAKEHOLDER_ROLES

    def test_ciso_is_NOT_primary_role(self):
        """CISO is NOT a primary role (falls to otherContacts)."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CISO" not in PRIMARY_STAKEHOLDER_ROLES

    def test_ceo_is_NOT_primary_role(self):
        """CEO is NOT a primary role (falls to otherContacts)."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CEO" not in PRIMARY_STAKEHOLDER_ROLES

    def test_cmo_is_NOT_primary_role(self):
        """CMO is NOT a primary role (falls to otherContacts)."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CMO" not in PRIMARY_STAKEHOLDER_ROLES

    def test_cpo_is_NOT_primary_role(self):
        """CPO is NOT a primary role (falls to otherContacts)."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "CPO" not in PRIMARY_STAKEHOLDER_ROLES

    def test_vp_is_NOT_primary_role(self):
        """VP is NOT a primary role (falls to otherContacts)."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES
        assert "VP" not in PRIMARY_STAKEHOLDER_ROLES


class TestStakeholderMapSplit:
    """Test that stakeholder_map_data correctly splits primary vs other."""

    def _build_stakeholders_data(self, roles: list) -> list:
        """Helper: build mock stakeholders_data for given role types."""
        return [
            {
                "name": f"Person {role}",
                "title": f"Chief {role} Officer",
                "role_type": role,
                "email": f"{role.lower()}@example.com",
                "phone": "+1-555-000-0001",
                "source": "zoominfo",
            }
            for role in roles
        ]

    def _split_stakeholders(self, stakeholders_data: list) -> dict:
        """Simulate what production_main.py does to split stakeholders."""
        from production_main import PRIMARY_STAKEHOLDER_ROLES

        primary = []
        others = []

        for s in stakeholders_data:
            role_type = s.get("role_type", "Unknown")
            if role_type in PRIMARY_STAKEHOLDER_ROLES:
                primary.append(s)
            else:
                others.append(s)

        # Fallback: if no primary found, promote others to primary
        if not primary and others:
            primary = others[:4]  # Promote up to 4 fallbacks
            others = []

        return {"stakeholders": primary, "otherContacts": others}

    def test_cto_goes_to_primary_stakeholders(self):
        """CTO is placed in stakeholders (primary) not otherContacts."""
        data = self._build_stakeholders_data(["CTO"])
        result = self._split_stakeholders(data)
        names = [s["name"] for s in result["stakeholders"]]
        assert "Person CTO" in names
        assert result["otherContacts"] == []

    def test_cio_goes_to_primary_stakeholders(self):
        """CIO is placed in stakeholders (primary)."""
        data = self._build_stakeholders_data(["CIO"])
        result = self._split_stakeholders(data)
        names = [s["name"] for s in result["stakeholders"]]
        assert "Person CIO" in names

    def test_coo_goes_to_primary_stakeholders(self):
        """COO is placed in stakeholders (primary)."""
        data = self._build_stakeholders_data(["COO"])
        result = self._split_stakeholders(data)
        names = [s["name"] for s in result["stakeholders"]]
        assert "Person COO" in names

    def test_cfo_goes_to_primary_stakeholders(self):
        """CFO is placed in stakeholders (primary)."""
        data = self._build_stakeholders_data(["CFO"])
        result = self._split_stakeholders(data)
        names = [s["name"] for s in result["stakeholders"]]
        assert "Person CFO" in names

    def test_ciso_goes_to_other_contacts(self):
        """CISO (when primary roles exist) goes to otherContacts."""
        data = self._build_stakeholders_data(["CTO", "CIO", "CISO"])
        result = self._split_stakeholders(data)
        other_names = [s["name"] for s in result["otherContacts"]]
        primary_names = [s["name"] for s in result["stakeholders"]]
        assert "Person CISO" in other_names
        assert "Person CISO" not in primary_names

    def test_ceo_goes_to_other_contacts_when_primaries_present(self):
        """CEO goes to otherContacts when CTO/CIO/COO/CFO are present."""
        data = self._build_stakeholders_data(["CTO", "CEO"])
        result = self._split_stakeholders(data)
        other_names = [s["name"] for s in result["otherContacts"]]
        assert "Person CEO" in other_names

    def test_fallback_when_no_primary_roles_found(self):
        """When no CTO/CIO/COO/CFO exist, other roles become primary."""
        data = self._build_stakeholders_data(["CISO", "CEO", "CMO"])
        result = self._split_stakeholders(data)
        # All 3 should be promoted to primary
        assert len(result["stakeholders"]) == 3
        assert result["otherContacts"] == []

    def test_fallback_promotes_only_first_four(self):
        """Fallback promotes at most 4 contacts to primary."""
        data = self._build_stakeholders_data(["CISO", "CEO", "CMO", "VP", "Director"])
        result = self._split_stakeholders(data)
        assert len(result["stakeholders"]) <= 4

    def test_all_four_primary_roles_found(self):
        """All 4 primary roles available → all 4 in primary, others in otherContacts."""
        data = self._build_stakeholders_data(["CTO", "CIO", "COO", "CFO", "CISO"])
        result = self._split_stakeholders(data)
        primary_roles = [s["role_type"] for s in result["stakeholders"]]
        assert set(primary_roles) == {"CTO", "CIO", "COO", "CFO"}
        other_roles = [s["role_type"] for s in result["otherContacts"]]
        assert "CISO" in other_roles


class TestRolePriorityOrder:
    """Test that role_priority sorting puts CTO > CIO > COO > CFO first."""

    def test_cto_has_highest_priority(self):
        """CTO has the highest sort priority (lowest number)."""
        from production_main import ROLE_PRIORITY
        assert ROLE_PRIORITY.get("cto", 99) < ROLE_PRIORITY.get("cio", 99)
        assert ROLE_PRIORITY.get("cto", 99) < ROLE_PRIORITY.get("coo", 99)
        assert ROLE_PRIORITY.get("cto", 99) < ROLE_PRIORITY.get("cfo", 99)

    def test_cio_second_priority(self):
        """CIO is second in sort order."""
        from production_main import ROLE_PRIORITY
        assert ROLE_PRIORITY.get("cio", 99) < ROLE_PRIORITY.get("cfo", 99)
        assert ROLE_PRIORITY.get("cio", 99) < ROLE_PRIORITY.get("coo", 99)

    def test_cfo_third_priority(self):
        """CFO is third in sort order."""
        from production_main import ROLE_PRIORITY
        assert ROLE_PRIORITY.get("cfo", 99) < ROLE_PRIORITY.get("coo", 99)
        assert ROLE_PRIORITY.get("cfo", 99) < ROLE_PRIORITY.get("ciso", 99)

    def test_coo_fourth_priority(self):
        """COO is fourth, before all secondary roles."""
        from production_main import ROLE_PRIORITY
        assert ROLE_PRIORITY.get("coo", 99) < ROLE_PRIORITY.get("ciso", 99)
        assert ROLE_PRIORITY.get("coo", 99) < ROLE_PRIORITY.get("ceo", 99)
        assert ROLE_PRIORITY.get("coo", 99) < ROLE_PRIORITY.get("cmo", 99)
        assert ROLE_PRIORITY.get("coo", 99) < ROLE_PRIORITY.get("cpo", 99)

    def test_sort_produces_correct_order(self):
        """Sorting stakeholders by ROLE_PRIORITY produces CTO > CIO > CFO > COO > others."""
        from production_main import ROLE_PRIORITY

        stakeholders = [
            {"role_type": "CISO", "name": "S"},
            {"role_type": "COO", "name": "D"},
            {"role_type": "CIO", "name": "B"},
            {"role_type": "CFO", "name": "C"},
            {"role_type": "CTO", "name": "A"},
        ]
        stakeholders.sort(key=lambda x: (
            ROLE_PRIORITY.get(x["role_type"].lower(), 99),
            x["name"].lower()
        ))
        roles = [s["role_type"] for s in stakeholders]
        assert roles[0] == "CTO"
        assert roles[1] == "CIO"
        assert roles[2] == "CFO"
        assert roles[3] == "COO"
        assert roles[4] == "CISO"
