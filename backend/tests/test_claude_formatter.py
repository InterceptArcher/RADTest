"""Unit tests for the pure parts of the Stage-5 Claude formatter (no SDK)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from contextlib import contextmanager  # noqa: E402


@contextmanager
def raises(exc_type):
    """Tiny pytest.raises stand-in so this file runs with or without pytest."""
    try:
        yield
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__} to be raised")


from claude_formatter import (  # noqa: E402
    FACTUAL_COMPANY_TOKENS, is_factual_token, build_factual_replacements,
    authored_tokens, outreach_greeting, council_contact_payload,
    validate_formatter_output, build_formatter_prompt,
    FormatterOutputInvalidError, FormatterSlotMismatchError, _extract_json,
)
from bi_resolver import StakeholderRecord, no_contact_sentinel  # noqa: E402


def test_factual_vs_authored_split():
    assert is_factual_token("[Private]")
    assert not is_factual_token("[Some authored overview blurb]")
    toks = ["[Private]", "[Aviva Canada]", "[Authored overview...]"]
    assert authored_tokens(toks) == ["[Authored overview...]"]


def test_build_factual_replacements_from_facts():
    facts = {"company_name": "Globex", "company_type": "Public",
             "industry": "Manufacturing", "estimated_it_spend": "$10M-$20M",
             "salesperson_name": "Dana Rep", "pull_date": "2026-06-23"}
    toks = list(FACTUAL_COMPANY_TOKENS.keys()) + ["[authored]"]
    repl = build_factual_replacements(toks, facts)
    assert repl["[Private]"] == "Public"             # account-type token -> fact
    assert repl["[Aviva Canada]"] == "Globex"
    assert repl["[Insurance – Property and Casualty]"] == "Manufacturing"
    assert "[authored]" not in repl


def test_outreach_greeting_slash_joins_and_skips_sentinels():
    contacts = [
        StakeholderRecord(persona="CFO", name="Lisa Leo"),
        StakeholderRecord(persona="CFO", name="Marcus Vale"),
        no_contact_sentinel("CFO"),
    ]
    assert outreach_greeting(contacts) == "Lisa/Marcus"


def test_council_payload_is_minimal_and_excludes_sentinels():
    slide = {
        "CTO": [StakeholderRecord(persona="CTO", name="T", title="CTO", email="t@a.com",
                                  linkedin_url="https://li/t", start_date="2024")],
        "CISO": [no_contact_sentinel("CISO")],
    }
    payload = council_contact_payload(slide)
    assert len(payload) == 1
    assert set(payload[0].keys()) == {"persona", "name", "title", "email", "linkedin_url", "start_date"}


def test_validate_output_ok():
    validate_formatter_output({"[a]": "x", "[b]": "y"}, {"[a]", "[b]"})  # no raise


def test_validate_output_missing_raises():
    with raises(FormatterOutputInvalidError):
        validate_formatter_output({"[a]": "x"}, {"[a]", "[b]"})


def test_validate_output_unknown_raises():
    with raises(FormatterSlotMismatchError):
        validate_formatter_output({"[a]": "x", "[z]": "?"}, {"[a]"})


def test_build_prompt_contains_facts_and_tokens():
    system, user = build_formatter_prompt({"company_name": "Globex"}, ["[overview]"])
    assert "no SKUs" in system
    assert "Globex" in user and "[overview]" in user


def test_extract_json_handles_code_fence():
    assert _extract_json('```json\n{"[a]": "x"}\n```') .strip() == '{"[a]": "x"}'
    assert _extract_json('noise {"[a]": "x"} trailing') == '{"[a]": "x"}'
