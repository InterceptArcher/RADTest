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
