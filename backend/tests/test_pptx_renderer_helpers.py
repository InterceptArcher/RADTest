"""Unit tests for the pure helpers + token classifier in pptx_renderer.py.

The python-pptx clone/fill/upload path is covered in CI (python-pptx is not
installable in this environment); these tests cover everything that is pure.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from pptx_renderer import (  # noqa: E402
    extract_tokens, replace_tokens, replace_tokens_in_runs, first_name,
    join_first_names, classify_contact_token, value_for_field,
    build_contact_replacements, missing_required_contact_values,
)
from bi_resolver import StakeholderRecord  # noqa: E402


def test_extract_tokens_distinct_in_order():
    text = "[Company] makes [Product] for [Company]"
    assert extract_tokens(text) == ["[Company]", "[Product]"]


def test_replace_tokens_basic():
    out = replace_tokens("Hello [Name] at [Co]", {"[Name]": "Lisa", "[Co]": "Aviva"})
    assert out == "Hello Lisa at Aviva"


def test_replace_tokens_longest_first_no_partial_clobber():
    text = "[Cloud Migration] and [Cloud Migration Strategy]"
    out = replace_tokens(text, {
        "[Cloud Migration]": "CM",
        "[Cloud Migration Strategy]": "CMS",
    })
    assert out == "CM and CMS"  # the longer token wasn't corrupted by the shorter


def test_replace_value_with_brackets_not_rescanned():
    # A value containing brackets must not trigger a second substitution.
    out = replace_tokens("[A]", {"[A]": "see [B]", "[B]": "SHOULD_NOT_APPEAR"})
    assert out == "see [B]"


def test_replace_tokens_in_runs_handles_split_token():
    runs = ["[Aviva ", "Canada]", " HQ"]
    out = replace_tokens_in_runs(runs, {"[Aviva Canada]": "Aviva Canada Inc"})
    assert out == ["Aviva Canada Inc HQ", "", ""]


def test_replace_tokens_in_runs_preserves_separate_runs():
    # Label run + value-token run (the contact-detail case): the value must be
    # replaced IN ITS OWN RUN so the bold label doesn't bleed onto the value.
    runs = ["Title: ", "[Technical Chief & Underwriter]"]
    out = replace_tokens_in_runs(runs, {"[Technical Chief & Underwriter]": "CFO"})
    assert out == ["Title: ", "CFO"]  # two runs preserved, not collapsed into one


def test_first_name_and_join():
    assert first_name("Lisa Leo") == "Lisa"
    assert join_first_names(["Lisa Leo", "Marcus Vale", "Lisa Other"]) == "Lisa/Marcus"


def test_classify_every_contact_slide_token():
    expected = {
        "[CTO]": "persona",
        "[Lisa Leo]": "name",
        "[Technical Chief & Underwriter]": "title",
        "[Technology]": "department",
        "[July 2025]": "start_date",
        "[(800) 387-4518]": "direct_phone",
        "[(647) 209-7349]": "mobile_phone",
        "[lisa_leo@avivacanada.com]": "email",
        "[https://www.linkedin.com/in/lisa-leo/]": "linkedin_url",
        "[Phone / Email / LinedIn]": "communication_preference",
        "[Lisa Leo is the Technical Chief and Underwriter at Aviva Canada...]": "about",
        "[Underwriting Technology Modernization - advancing the stack...]": "strategic_priorities",
        "[Engage Lisa by demonstrating how your solution bridges...]": "conversation_starters",
    }
    for token, field in expected.items():
        assert classify_contact_token(token) == field, f"{token!r} -> {field}"


def test_classify_unknown_token_returns_none():
    assert classify_contact_token("[Some Random Marketing Blurb]") is None


def test_value_for_field_joins_lists():
    c = StakeholderRecord(persona="CTO", name="Lisa Leo",
                          strategic_priorities=["Modernize stack", "Data enablement"])
    assert value_for_field(c, "name") == "Lisa Leo"
    assert value_for_field(c, "strategic_priorities") == "Modernize stack\nData enablement"


def test_build_contact_replacements_maps_present_tokens():
    c = StakeholderRecord(persona="CFO", name="Jane Roe", title="Chief Financial Officer",
                          email="jane@acme.com", linkedin_url="https://li/jane",
                          start_date="2023-03", department="Finance")
    tokens = ["[CTO]", "[Lisa Leo]", "[Technical Chief & Underwriter]", "[Technology]",
              "[lisa_leo@avivacanada.com]", "[https://www.linkedin.com/in/lisa-leo/]",
              "[July 2025]", "[Unmapped Marketing Token]"]
    repl = build_contact_replacements(c, tokens)
    assert repl["[CTO]"] == "CFO"
    assert repl["[Lisa Leo]"] == "Jane Roe"
    assert repl["[Technical Chief & Underwriter]"] == "Chief Financial Officer"
    assert repl["[lisa_leo@avivacanada.com]"] == "jane@acme.com"
    assert "[Unmapped Marketing Token]" not in repl  # left for company-slot mapping


def test_missing_required_contact_values_flags_gaps():
    incomplete = StakeholderRecord(persona="CIO", name="No Email", title="CIO",
                                   linkedin_url="https://li/x", start_date="2024")
    missing = missing_required_contact_values({}, incomplete)
    assert "email" in missing


def test_sentinel_contact_is_allowed_to_ship():
    from bi_resolver import no_contact_sentinel
    s = no_contact_sentinel("CISO")
    assert missing_required_contact_values({}, s) == []
