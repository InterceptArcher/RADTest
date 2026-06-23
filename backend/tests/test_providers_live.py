"""Tests for the live providers adapter — pure helpers + async wiring on fakes."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from providers_live import persona_titles_for, zi_person_to_record, LiveProviders  # noqa: E402
from bi_resolver import StakeholderRecord, CanonicalCompany  # noqa: E402


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --- fakes -------------------------------------------------------------------

class _Block:
    def __init__(self, text): self.text = text


class _Resp:
    def __init__(self, text): self.content = [_Block(text)]


class FakeMessages:
    def __init__(self, text): self._text = text
    async def create(self, **kwargs): return _Resp(self._text)


class FakeAnthropic:
    def __init__(self, text): self.messages = FakeMessages(text)


class FakeZI:
    def __init__(self, people=None, normalized=None):
        self._people = people or []
        self._normalized = normalized or {}
    async def search_contacts(self, domain, job_titles=None, max_results=25):
        return {"success": True, "people": self._people, "error": None}
    async def enrich_company(self, domain=None, company_name=None):
        return {"success": True, "normalized": self._normalized}


CANON = CanonicalCompany(name="Acme", primary_domain="acme.com")


# --- pure helpers ------------------------------------------------------------

def test_persona_titles_csuite_includes_exact_and_adjacent():
    joined = " ".join(persona_titles_for("CTO", "csuite")).lower()
    assert "chief technology officer" in joined and "vp of engineering" in joined


def test_persona_titles_vp_and_director_hints():
    assert persona_titles_for("CISO", "vp") == ["VP of Security", "VP of Information Security", "VP of Cybersecurity"]
    assert persona_titles_for("CFO", "director")[0].startswith("Director of Finance")


def test_zi_person_to_record_maps_fields():
    rec = zi_person_to_record({"first_name": "Lisa", "last_name": "Leo", "title": "CTO",
                               "email": "lisa@acme.com", "linkedin": "https://li/lisa",
                               "hire_date": "2024-07", "department": "Technology"}, "CTO")
    assert rec.name == "Lisa Leo" and rec.email == "lisa@acme.com"
    assert rec.start_date == "2024-07" and "zoominfo" in rec.email_sources


# --- async wiring ------------------------------------------------------------

def test_query_maps_zi_people_to_records():
    zi = FakeZI(people=[{"first_name": "A", "last_name": "B", "title": "CTO",
                         "email": "a@acme.com", "linkedin": "https://li/a"}])
    lp = LiveProviders(zi_client=zi)
    recs = run(lp.query("CTO", "zoominfo", "csuite", CANON, False))
    assert len(recs) == 1 and recs[0].name == "A B" and recs[0].source == "zoominfo"


def test_query_canada_only_flags_limitation():
    zi = FakeZI(people=[{"first_name": "A", "last_name": "B", "title": "CTO", "email": "a@acme.com"}])
    recs = run(LiveProviders(zi_client=zi).query("CTO", "zoominfo", "csuite", CANON, True))
    assert any("canada_only_requested" in m for m in recs[0].marks)


def test_query_noop_for_non_csuite_or_non_zoominfo():
    zi = FakeZI(people=[{"first_name": "A", "last_name": "B"}])
    lp = LiveProviders(zi_client=zi)
    assert run(lp.query("CTO", "zoominfo", "vp", CANON, False)) == []
    assert run(lp.query("CTO", "apollo", "csuite", CANON, False)) == []


def test_judge_adjacency_parses_yes_no():
    yes = LiveProviders(anthropic_client=FakeAnthropic("yes"))
    no = LiveProviders(anthropic_client=FakeAnthropic("No, unrelated."))
    assert run(yes.judge_adjacency("Chief Code Officer", "CTO")) is True
    assert run(no.judge_adjacency("Head of Catering", "CTO")) is False


def test_enrich_sets_start_date_only_with_citation():
    rec = StakeholderRecord(persona="CTO", name="A", linkedin_url="https://li/a")
    lp = LiveProviders(anthropic_client=FakeAnthropic(
        '{"start_date":"2022-05","current_position_confirmed":true,"extracted_snippet":"Joined May 2022","source_url":"https://li/a"}'))
    out = run(lp.enrich(rec))
    assert out.start_date == "2022-05" and "linkedin_start_date_verified" in out.marks


def test_enrich_rejects_uncited_start_date():
    rec = StakeholderRecord(persona="CTO", name="A", linkedin_url="https://li/a")
    lp = LiveProviders(anthropic_client=FakeAnthropic('{"start_date":"2022","extracted_snippet":""}'))
    out = run(lp.enrich(rec))
    assert out.start_date == "" and any("no_citation" in m for m in out.marks)


def test_enrich_skips_when_already_complete():
    rec = StakeholderRecord(persona="CTO", name="A", linkedin_url="https://li/a", start_date="2020")
    # no anthropic configured + no env key -> would mark if it ran; assert it didn't
    out = run(LiveProviders().enrich(rec))
    assert out.start_date == "2020" and out.marks == []


def test_fallback_returns_none_without_source():
    lp = LiveProviders(anthropic_client=FakeAnthropic('{"name":"X","title":"CTO"}'))  # no source_url
    assert run(lp.fallback("CTO", CANON, False)) is None


def test_fallback_returns_record_with_source():
    lp = LiveProviders(anthropic_client=FakeAnthropic(
        '{"name":"Jane Doe","title":"CTO","linkedin_url":"https://li/j","source_url":"https://news/x"}'))
    rec = run(lp.fallback("CTO", CANON, False))
    assert rec is not None and rec.name == "Jane Doe" and rec.source == "agent"


def test_resolve_company_from_zi_normalized():
    zi = FakeZI(normalized={"company_name": "Acme Inc", "domain": "acme.com", "industry": "Tech",
                            "country": "USA", "employee_count": 500})
    canon = run(LiveProviders(zi_client=zi).resolve_company({"company_name": "Acme", "domain": "acme.com"}))
    assert canon.name == "Acme Inc" and canon.industry == "Tech" and canon.confidence == 0.8
