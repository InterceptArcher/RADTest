"""Pure-helper tests for the live providers adapter (no network/SDK)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from providers_live import persona_titles_for, zi_person_to_record  # noqa: E402


def test_persona_titles_csuite_includes_exact_and_adjacent():
    titles = persona_titles_for("CTO", "csuite")
    joined = " ".join(titles).lower()
    assert "chief technology officer" in joined
    assert "vp of engineering" in joined


def test_persona_titles_vp_and_director_hints():
    assert persona_titles_for("CISO", "vp") == ["VP of Security", "VP of Information Security", "VP of Cybersecurity"]
    assert persona_titles_for("CFO", "director")[0].startswith("Director of Finance")


def test_zi_person_to_record_maps_fields():
    rec = zi_person_to_record({
        "first_name": "Lisa", "last_name": "Leo", "title": "CTO",
        "email": "lisa@acme.com", "direct_phone": "555", "linkedin": "https://li/lisa",
        "hire_date": "2024-07", "department": "Technology",
    }, "CTO")
    assert rec.name == "Lisa Leo" and rec.title == "CTO"
    assert rec.email == "lisa@acme.com" and rec.start_date == "2024-07"
    assert rec.linkedin_url == "https://li/lisa" and rec.source == "zoominfo"
    assert "zoominfo" in rec.email_sources
