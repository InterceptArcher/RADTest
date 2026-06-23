"""Tests for the flag-gated v3.1 hook core (assemble_v31) + formatter.build (fakes)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from bi_resolver import StakeholderRecord, CanonicalCompany, MIN_SLIDES  # noqa: E402
from claude_formatter import ClaudeFormatter  # noqa: E402
from pipeline_v31_hook import assemble_v31, _serialize, estimate_it_spend, deck_basename  # noqa: E402


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _complete(persona, name):
    return StakeholderRecord(persona=persona, name=name, title="Chief X Officer",
                             email=f"{name}@a.com", linkedin_url=f"https://li/{name}",
                             start_date="2024", source="zoominfo", tier=1, proximity=0)


class FakeProviders:
    def __init__(self):
        self.table = {
            ("CIO", "zoominfo", "csuite"): [_complete("CIO", "Ivy")],
            ("CTO", "zoominfo", "csuite"): [_complete("CTO", "Tom")],
            ("CFO", "zoominfo", "csuite"): [_complete("CFO", "Fay")],
            ("COO", "zoominfo", "csuite"): [_complete("COO", "Omar")],
        }
    async def query(self, persona, source, kind, canonical, canada_only):
        return list(self.table.get((persona, source, kind), []))
    async def judge_adjacency(self, title, persona): return True
    async def enrich(self, record): return record
    async def fallback(self, persona, canonical, canada_only): return None


class FakeFormatter:
    def __init__(self): self.seen_tokens = None
    async def build(self, facts, company_tokens, slide_contacts):
        self.seen_tokens = company_tokens
        return {"company_slots": {t: "copy" for t in company_tokens},
                "outreach_slots": {p: {"greeting": "/".join(c.name.split()[0] for c in cs)}
                                   for p, cs in slide_contacts.items() if cs}}


class FakeRenderer:
    def __init__(self): self.render_args = None
    def introspect_company_tokens(self): return ["[Aviva Canada]", "[Overview blurb]"]
    async def render(self, *, slide_contacts, company_slots, outreach_slots, job_id):
        self.render_args = (slide_contacts, company_slots, outreach_slots)
        return f"https://supabase/decks/{job_id}.pptx"


def test_assemble_v31_runs_contacts_then_renders():
    renderer = FakeRenderer()
    out = run(assemble_v31(FakeProviders(), FakeFormatter(), renderer,
                           CanonicalCompany(name="Globex", primary_domain="g.com"),
                           {"company_name": "Globex"}, "job9", False))
    sel = out["selection"]
    assert sum(len(v) for v in sel.slide_contacts.values()) >= MIN_SLIDES
    assert out["slideshow_url"].endswith("job9.pptx")
    # renderer received the formatter's assembled slots
    assert renderer.render_args[1]["[Overview blurb]"] == "copy"


def test_serialize_produces_plain_dicts():
    out = _serialize({"CTO": [_complete("CTO", "Tom")], "CIO": []})
    assert out["CTO"][0]["name"] == "Tom" and out["CIO"] == []
    assert isinstance(out["CTO"][0], dict)


def test_formatter_build_splits_factual_and_authored():
    f = ClaudeFormatter()

    async def fake_author(facts, tokens):  # avoid the real Anthropic call
        return {t: "AUTHORED" for t in tokens}

    f.author = fake_author
    facts = {"company_type": "Public", "company_name": "Globex"}
    tokens = ["[Private]", "[Aviva Canada]", "[Some authored overview]"]
    contacts = {"CFO": [_complete("CFO", "Fay Roe"), _complete("CFO", "Max Vale")]}
    out = run(f.build(facts, tokens, contacts))
    cs = out["company_slots"]
    assert cs["[Private]"] == "Public"           # factual -> company_type
    assert cs["[Aviva Canada]"] == "Globex"      # factual -> company_name
    assert cs["[Some authored overview]"] == "AUTHORED"
    # outreach map is keyed by the master's example token strings now
    assert out["outreach_slots"]["CFO"]["[Lisa]"] == "Fay/Max"
    assert out["outreach_slots"]["CFO"]["[Aviva Canada]"] == "Globex"


# --- #2 IT-budget estimate ---------------------------------------------------

def test_it_spend_explicit_top_level_wins():
    assert estimate_it_spend({"estimated_it_spend": "$43.1M – $86.2M annually"}) == "$43.1M – $86.2M annually"


def test_it_spend_from_nested_executive_snapshot():
    facts = {"executive_snapshot": {"estimated_it_spend": "$5-$10 million annually"}}
    assert estimate_it_spend(facts) == "$5-$10 million annually"


def test_it_spend_from_council_display_variant():
    # it_spend_estimator council member emits *_display, not estimated_it_spend.
    facts = {"executive_snapshot": {"estimated_it_spend_display": "$12-$18 million"}}
    assert estimate_it_spend(facts) == "$12-$18 million"


def test_it_spend_computed_from_employee_count():
    out = estimate_it_spend({"employee_count": 5000})
    assert out == "$50.0M – $100.0M annually"  # 5000 * $10k–$20k


def test_it_spend_employee_count_string_and_small_company():
    assert estimate_it_spend({"employee_count": "2,500"}).endswith("annually")
    small = estimate_it_spend({"employee_count": 30})
    assert "K" in small and "M" not in small  # 30 * $10k–$20k -> $300K–$600K


def test_it_spend_computed_from_revenue_when_no_headcount():
    out = estimate_it_spend({"annual_revenue": "$198.3 billion"})
    assert out == "$5.9B – $9.9B annually"  # 3%–5% of revenue, billions formatting


def test_it_spend_blank_when_nothing_to_estimate_from():
    assert estimate_it_spend({"company_name": "Acme"}) == ""


def test_deck_basename_slugifies_company_and_date():
    assert deck_basename("Microsoft", "2026-06-23") == "hprad_microsoft_2026-06-23"
    # punctuation/spaces collapse to single underscores; trimmed at the ends
    assert deck_basename("AT&T, Inc.", "2026-06-23") == "hprad_at_t_inc_2026-06-23"
    assert deck_basename("  Coca-Cola  ", "2026-06-23") == "hprad_coca_cola_2026-06-23"


def test_deck_basename_blank_company_falls_back():
    assert deck_basename("", "2026-06-23") == "hprad_company_2026-06-23"


def _mkrec(persona, name, *, email="", phone="", linkedin="", prox=None):
    from bi_resolver import StakeholderRecord, Proximity
    r = StakeholderRecord(persona=persona, name=name, title="X",
                          proximity=int(prox if prox is not None else Proximity.UNKNOWN))
    r.email, r.phone, r.linkedin_url = email, phone, linkedin
    return r


def test_quality_keeps_pick_meeting_baseline():
    # A relevant pick with email+LinkedIn (no phone) MEETS baseline -> kept as-is.
    from pipeline_v31_hook import _enforce_contact_quality
    from bi_resolver import SelectionResult, Proximity
    cfo = _mkrec("CFO", "Real CFO", email="cfo@x.com", linkedin="https://li/cfo", prox=Proximity.EXACT)
    sel = SelectionResult(slide_contacts={"CFO": [cfo]}, contact_catalogue={"CFO": [cfo]},
                          enrichment_trace=[], warnings=[])

    class FakeP:
        async def enrich_one(self, c, company, domain=""):
            pass

    run(_enforce_contact_quality(sel, FakeP(), "Acme", "acme.com", floor=1))
    assert [c.name for c in sel.slide_contacts["CFO"]] == ["Real CFO"]


def test_quality_replaces_below_baseline_pick():
    # Pick has LinkedIn only (no email) -> below baseline -> REPLACED by a catalogue
    # contact that can be enriched to baseline (email+LinkedIn).
    from pipeline_v31_hook import _enforce_contact_quality
    from bi_resolver import SelectionResult, Proximity
    top = _mkrec("CFO", "No Email Exec", linkedin="https://li/top", prox=Proximity.EXACT)
    alt = _mkrec("CFO", "Reachable Alt", prox=Proximity.CANONICAL)
    sel = SelectionResult(slide_contacts={"CFO": [top]}, contact_catalogue={"CFO": [top, alt]},
                          enrichment_trace=[], warnings=[])

    class FakeP:
        async def enrich_one(self, c, company, domain=""):
            if c.name == "Reachable Alt":
                c.email, c.phone, c.linkedin_url = "alt@x.com", "+1", "https://li/alt"

    run(_enforce_contact_quality(sel, FakeP(), "Acme", "acme.com", floor=1))
    assert [c.name for c in sel.slide_contacts["CFO"]] == ["Reachable Alt"]


def test_quality_drops_below_baseline_pick_with_no_replacement():
    # Below-baseline pick and no catalogue contact can reach baseline -> persona dropped
    # (a name a rep can't reach is not shown).
    from pipeline_v31_hook import _enforce_contact_quality
    from bi_resolver import SelectionResult, Proximity
    top = _mkrec("CFO", "No Email Exec", linkedin="https://li/top", prox=Proximity.EXACT)
    sel = SelectionResult(slide_contacts={"CFO": [top]}, contact_catalogue={"CFO": [top]},
                          enrichment_trace=[], warnings=[])

    class FakeP:
        async def enrich_one(self, c, company, domain=""):
            pass  # nothing reaches baseline

    run(_enforce_contact_quality(sel, FakeP(), "Acme", "acme.com", floor=1))
    assert sel.slide_contacts["CFO"] == []  # dropped


def test_quality_floor_backfills_to_four_baseline_contacts():
    from pipeline_v31_hook import _enforce_contact_quality
    from bi_resolver import SelectionResult, Proximity
    cio = _mkrec("CIO", "Real CIO", email="cio@x.com", phone="+1", linkedin="https://li/cio", prox=Proximity.EXACT)
    sel = SelectionResult(
        slide_contacts={"CIO": [cio], "CFO": [_mkrec("CFO", "Web CFO", linkedin="https://li/wcfo")],
                        "COO": [_mkrec("COO", "Web COO", linkedin="https://li/wcoo")],
                        "CTO": [_mkrec("CTO", "Web CTO", linkedin="https://li/wcto")]},
        contact_catalogue={"CIO": [cio],
                           "CFO": [_mkrec("CFO", "Complete A")],
                           "COO": [_mkrec("COO", "Complete B")],
                           "CTO": [_mkrec("CTO", "Complete C")]},
        enrichment_trace=[], warnings=[])

    class FakeP:
        async def enrich_one(self, c, company, domain=""):
            if c.name.startswith("Complete"):
                c.email, c.phone, c.linkedin_url = f"{c.name}@x.com", "+1", f"https://li/{c.name}"

    run(_enforce_contact_quality(sel, FakeP(), "Acme", "acme.com", floor=4))
    baseline = [c.name for v in sel.slide_contacts.values() for c in v if c.email and c.linkedin_url]
    assert len(baseline) >= 4, baseline
    assert "Real CIO" in baseline  # relevant+reachable pick kept


def test_deck_basename_canada_only_suffix_avoids_collision():
    # The Canada-only run must not overwrite the company's global deck same-day.
    assert deck_basename("Microsoft", "2026-06-23", canada_only=True) == "hprad_microsoft_2026-06-23_ca"
    assert deck_basename("Microsoft", "2026-06-23") != deck_basename("Microsoft", "2026-06-23", canada_only=True)
