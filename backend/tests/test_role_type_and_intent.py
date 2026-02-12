"""
Tests for role type inference and intent score normalization.
TDD - write failing tests first.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_main import _infer_role_type, _normalize_intent_score


class TestInferRoleType:
    """Test _infer_role_type correctly classifies job titles."""

    def test_vice_president_not_classified_as_ceo(self):
        """VP titles must NOT match CEO - this was the original bug."""
        assert _infer_role_type("Vice President of Sales") == "VP"
        assert _infer_role_type("Vice President of Engineering") == "VP"
        assert _infer_role_type("Vice President") == "VP"

    def test_president_classified_as_ceo(self):
        """Standalone 'President' should be CEO."""
        assert _infer_role_type("President") == "CEO"
        assert _infer_role_type("President and CEO") == "CEO"

    def test_svp_evp_classified_as_vp(self):
        """SVP and EVP are VP-level."""
        assert _infer_role_type("SVP of Operations") == "VP"
        assert _infer_role_type("EVP, Global Sales") == "VP"

    def test_csuite_roles(self):
        """All C-suite roles should be correctly classified."""
        assert _infer_role_type("Chief Information Officer") == "CIO"
        assert _infer_role_type("CTO") == "CTO"
        assert _infer_role_type("Chief Information Security Officer") == "CISO"
        assert _infer_role_type("Chief Operating Officer") == "COO"
        assert _infer_role_type("Chief Financial Officer") == "CFO"
        assert _infer_role_type("Chief Product Officer") == "CPO"
        assert _infer_role_type("Chief Executive Officer") == "CEO"
        assert _infer_role_type("Chief Marketing Officer") == "CMO"

    def test_director_classification(self):
        """Director titles should be classified as Director."""
        assert _infer_role_type("Director of Sales") == "Director"
        assert _infer_role_type("Senior Director, Operations") == "Director"
        # Note: "IT Director" maps to CIO (same functional role)
        assert _infer_role_type("IT Director") == "CIO"

    def test_manager_classification(self):
        """Manager titles should be classified as Manager."""
        assert _infer_role_type("IT Manager") == "Manager"
        assert _infer_role_type("Manager of Engineering") == "Manager"
        assert _infer_role_type("Senior Manager, Sales") == "Manager"

    def test_unknown_title(self):
        """Unknown titles should return 'Unknown'."""
        assert _infer_role_type("Software Engineer") == "Unknown"
        assert _infer_role_type("") == "Unknown"
        assert _infer_role_type(None) == "Unknown"

    def test_cio_specific_titles(self):
        """CIO-adjacent titles should resolve to CIO."""
        assert _infer_role_type("VP of IT") == "CIO"
        assert _infer_role_type("Head of IT") == "CIO"

    def test_cto_specific_titles(self):
        """CTO-adjacent titles should resolve to CTO."""
        assert _infer_role_type("VP of Engineering") == "CTO"
        assert _infer_role_type("Head of Engineering") == "CTO"

    def test_founder_is_ceo(self):
        """Founder/Co-founder should be CEO."""
        assert _infer_role_type("Founder") == "CEO"
        assert _infer_role_type("Co-Founder") == "CEO"

    def test_managing_director_is_ceo(self):
        """Managing Director should be CEO."""
        assert _infer_role_type("Managing Director") == "CEO"

    def test_case_insensitivity(self):
        """Should work regardless of case."""
        assert _infer_role_type("CHIEF INFORMATION OFFICER") == "CIO"
        assert _infer_role_type("vice president of sales") == "VP"
        assert _infer_role_type("Director Of Engineering") == "Director"


class TestNormalizeIntentScore:
    """Test _normalize_intent_score converts correctly to 0-100 scale."""

    def test_decimal_score_scaled_up(self):
        """Scores <= 1.0 should be multiplied by 100."""
        assert _normalize_intent_score(0.7) == 70
        assert _normalize_intent_score(0.5) == 50
        assert _normalize_intent_score(1.0) == 100
        assert _normalize_intent_score(0.0) == 0

    def test_percentage_score_unchanged(self):
        """Scores > 1.0 should stay as-is (already percentage)."""
        assert _normalize_intent_score(70) == 70
        assert _normalize_intent_score(50) == 50
        assert _normalize_intent_score(100) == 100

    def test_none_returns_default(self):
        """None should return 50 (medium)."""
        assert _normalize_intent_score(None) == 50

    def test_string_score_converted(self):
        """String numbers should be converted."""
        assert _normalize_intent_score("0.8") == 80
        assert _normalize_intent_score("75") == 75

    def test_invalid_returns_default(self):
        """Invalid values should return 50."""
        assert _normalize_intent_score("invalid") == 50
        assert _normalize_intent_score({}) == 50

    def test_clamped_to_100(self):
        """Scores > 100 should be clamped."""
        assert _normalize_intent_score(150) == 100

    def test_clamped_to_0(self):
        """Negative scores should be clamped to 0."""
        assert _normalize_intent_score(-10) == 0
