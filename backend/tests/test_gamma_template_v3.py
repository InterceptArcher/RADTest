"""
TDD tests for Gamma Template v3 (template g_uost7x0lutmwtwd).

Spec: docs/superpowers/specs/2026-05-04-gamma-template-v3-design.md

Patterns mirror tests/test_gamma_pending_recovery.py — synthetic
validated_data dicts, no real Gamma calls. Helpers and pure markdown
emitters are tested directly; the network-touching paths reuse the
FakeAsyncClient fixture pattern.
"""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Task 1: Template ID swap
# ---------------------------------------------------------------------------

def test_default_template_id_is_v3():
    """
    The new default template ID is g_uost7x0lutmwtwd. Both the constructor
    default and the instance-attribute fallback must reflect this.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    assert creator.template_id == "g_uost7x0lutmwtwd", (
        f"expected default template g_uost7x0lutmwtwd, got {creator.template_id!r}"
    )


def test_explicit_template_id_overrides_default():
    """Caller-supplied template_id wins over the default — sanity check."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(
        gamma_api_key="test-key",
        template_id="g_some_other_id",
    )
    assert creator.template_id == "g_some_other_id"


# ---------------------------------------------------------------------------
# Task 2: Account type normalization (5 → 4 bucket pass-through)
# ---------------------------------------------------------------------------

def test_normalize_account_type_passthrough_buckets():
    """Public, Private, Government, Non-Profit pass through verbatim."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("Public") == "Public"
    assert _normalize_account_type("Private") == "Private"
    assert _normalize_account_type("Government") == "Government"
    assert _normalize_account_type("Non-Profit") == "Non-Profit"


def test_normalize_account_type_subsidiary_to_private():
    """Subsidiary collapses to Private — held privately by parent."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("Subsidiary") == "Private"


def test_normalize_account_type_case_insensitive():
    """Accept lowercase and mixed-case variants from the LLM."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("public") == "Public"
    assert _normalize_account_type("PUBLIC") == "Public"
    assert _normalize_account_type("Publicly traded") == "Public"
    assert _normalize_account_type("government agency") == "Government"
    assert _normalize_account_type("non-profit organization") == "Non-Profit"
    assert _normalize_account_type("nonprofit") == "Non-Profit"


def test_normalize_account_type_unknown_defaults_to_private():
    """Empty / unrecognized strings default to Private."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("") == "Private"
    assert _normalize_account_type("???") == "Private"
    assert _normalize_account_type(None) == "Private"


# ---------------------------------------------------------------------------
# Task 3: Pain points format — bolded title + blank line + description
# ---------------------------------------------------------------------------

def _make_validated_with_pain_points():
    return {
        "company_name": "Acme Co",
        "domain": "acme.com",
        "validated_data": {"company_name": "Acme Co"},
        "pain_points": [
            {"title": "Aging device fleet",
             "description": "Most laptops are 4+ years old, hurting productivity."},
            {"title": "Inconsistent endpoint security",
             "description": "Mixed OS versions complicate patching and policy."},
            {"title": "Slow procurement cycle",
             "description": "Hardware refreshes take 90+ days vs industry 30."},
        ],
    }


def test_pain_points_format_template_path_emits_bold_title_blank_description():
    """
    The template-path formatter (_format_for_template) emits each pain point
    as **title** on its own line, then a blank line, then the description.
    Caps at 3 entries.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_pain_points()
    output = creator._format_for_template(company)

    assert "**Aging device fleet**" in output
    assert "Most laptops are 4+ years old, hurting productivity." in output
    assert "**Inconsistent endpoint security**" in output
    assert "Mixed OS versions complicate patching and policy." in output
    assert "**Slow procurement cycle**" in output

    # Each title must be followed by a blank line and then the description
    # (verify by checking the title and description appear in order with a
    # newline between them, not inline).
    idx_title_1 = output.index("**Aging device fleet**")
    idx_desc_1 = output.index("Most laptops are 4+ years old")
    between = output[idx_title_1:idx_desc_1]
    assert "\n\n" in between, (
        "expected blank line between title and description, got: " + repr(between)
    )


def test_pain_points_format_caps_at_three_entries():
    """Inputs of >3 entries truncate to 3."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_pain_points()
    company["pain_points"].append({"title": "Fourth", "description": "Should not render."})
    output = creator._format_for_template(company)
    assert "**Fourth**" not in output
    assert "Should not render." not in output


def test_pain_points_format_reads_fallback_chain():
    """
    If validated_data.pain_points is missing, the formatter falls through
    to opportunity_themes_detailed.pain_points, then opportunity_themes.pain_points.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Fallback Co",
        "validated_data": {"company_name": "Fallback Co"},
        "opportunity_themes_detailed": {
            "pain_points": [
                {"title": "Nested pain", "description": "From the detailed nest."},
            ],
        },
    }
    output = creator._format_for_template(company)
    assert "**Nested pain**" in output
    assert "From the detailed nest." in output
