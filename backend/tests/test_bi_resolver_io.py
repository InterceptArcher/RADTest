"""Async tests for the Stage 1/2/3 I/O orchestration (fakes + asyncio, no SDKs)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from bi_resolver import StakeholderRecord, PERSONAS, MIN_SLIDES, Proximity  # noqa: E402
from bi_resolver_io import (  # noqa: E402
    run_stage3, select_persona_contacts_io, normalize_company_key,
    should_reconcile, with_timeout,
)


def rec(persona, name, title="Chief X Officer", complete=True, linkedin=None):
    ln = linkedin if linkedin is not None else f"https://li/{name.lower()}"
    r = StakeholderRecord(persona=persona, name=name, title=title,
                          email=f"{name.lower()}@acme.com", linkedin_url=ln, start_date="2024")
    if not complete:
        r.email, r.start_date = "", ""
    return r


class FakeProviders:
    """Configurable fake: maps (persona, source, kind) -> candidate list."""

    def __init__(self, table=None, adjacency=True, enrich_fn=None, fallback_fn=None):
        self.table = table or {}
        self.adjacency = adjacency
        self.enrich_fn = enrich_fn or (lambda r: r)
        self.fallback_fn = fallback_fn
        self.queries = []  # records every (source, kind) actually queried

    async def query(self, persona, source, kind, canonical, canada_only):
        self.queries.append((persona, source, kind))
        return list(self.table.get((persona, source, kind), []))

    async def judge_adjacency(self, title, persona):
        return self.adjacency

    async def enrich(self, record):
        return self.enrich_fn(record)

    async def fallback(self, persona, canonical, canada_only):
        return self.fallback_fn(persona) if self.fallback_fn else None


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --- Stage 3 driver ----------------------------------------------------------

def test_zi_csuite_exact_used_and_stops():
    fp = FakeProviders({("CTO", "zoominfo", "csuite"): [rec("CTO", "Tess", "Chief Technology Officer")]})
    sel, _ = run(select_persona_contacts_io("CTO", fp, None, False, set()))
    assert [r.name for r in sel] == ["Tess"]
    # stopped after ZI csuite — never queried VP/Director/Apollo/PDL
    assert fp.queries == [("CTO", "zoominfo", "csuite")]


def test_short_circuit_skips_zi_director_to_apollo():
    fp = FakeProviders({
        ("CIO", "zoominfo", "csuite"): [],
        ("CIO", "zoominfo", "vp"): [],
        ("CIO", "apollo", "csuite"): [rec("CIO", "Ada", "Chief Information Officer")],
    })
    sel, _ = run(select_persona_contacts_io("CIO", fp, None, False, set()))
    assert [r.name for r in sel] == ["Ada"]
    kinds = [(s, k) for (_, s, k) in fp.queries]
    assert ("zoominfo", "director") not in kinds  # short-circuited
    assert ("apollo", "csuite") in kinds


def test_non_adjacent_title_rejected_via_judge():
    fp = FakeProviders(
        {("CFO", "zoominfo", "csuite"): [rec("CFO", "Bob", "Chief Burrito Officer")]},
        adjacency=False,
    )
    sel, exm = run(select_persona_contacts_io("CFO", fp, None, False, set()))
    assert sel == []  # judged not adjacent -> rejected, cascade continues/exhausts


def test_llm_adjacent_title_accepted():
    fp = FakeProviders(
        {("CFO", "zoominfo", "csuite"): [rec("CFO", "Ann", "Chief Money Wizard")]},
        adjacency=True,
    )
    sel, _ = run(select_persona_contacts_io("CFO", fp, None, False, set()))
    assert [r.name for r in sel] == ["Ann"]
    assert sel[0].proximity == int(Proximity.LLM_ADJACENT)


def test_cross_slide_dedupe_in_io():
    used = set()
    fp1 = FakeProviders({("CIO", "zoominfo", "csuite"): [rec("CIO", "Sam", "Chief Information Officer", linkedin="https://li/sam")]})
    s1, _ = run(select_persona_contacts_io("CIO", fp1, None, False, used))
    fp2 = FakeProviders({("CTO", "zoominfo", "csuite"): [rec("CTO", "Sam2", "Chief Technology Officer", linkedin="https://li/sam")]})
    s2, _ = run(select_persona_contacts_io("CTO", fp2, None, False, used))
    assert len(s1) == 1 and s2 == []


def test_run_stage3_floor_fill_with_fallback():
    table = {
        ("CTO", "zoominfo", "csuite"): [rec("CTO", "T", "Chief Technology Officer")],
        ("CIO", "zoominfo", "csuite"): [rec("CIO", "I", "Chief Information Officer")],
    }
    fp = FakeProviders(table, fallback_fn=lambda p: rec(p, f"Agent{p}", "Chief X Officer", linkedin=f"https://li/agent{p}"))
    result = run(run_stage3(fp, canonical=None))
    assert result.total_slides() >= MIN_SLIDES
    assert any("fallback_agent" in w or "relaxed" in w or "no_contact" in w for w in result.warnings)
    assert result.enrichment_trace


def test_floor_fill_prefers_web_agent_over_weak_catalogue_contact():
    # A persona whose ZI pool is ONLY a weak/UNKNOWN-title contact (the generic
    # large-domain pool) must floor-fill via the web agent (the real role-holder),
    # NOT keep the complete-but-wrong weak contact.
    weak = rec("CTO", "Wrong Person", title="Senior Manager, Comms")
    weak.proximity = int(Proximity.UNKNOWN)
    fp = FakeProviders(
        {("CTO", "zoominfo", "csuite"): [weak]},
        adjacency=False,  # weak title is judged non-adjacent -> stays UNKNOWN
        fallback_fn=lambda p: rec(p, "Real CTO", "Chief Technology Officer", linkedin="https://li/realcto"),
    )
    result = run(run_stage3(fp, canonical=None))
    cto = result.slide_contacts["CTO"]
    assert [c.name for c in cto] == ["Real CTO"]
    assert any("floor_fill_fallback_agent" in m for m in cto[0].marks)


def test_run_stage3_uncapped_co_equal():
    table = {("CFO", "zoominfo", "csuite"): [
        rec("CFO", "A", "Chief Financial Officer"),
        rec("CFO", "B", "Chief Financial Officer"),
    ]}
    # everything else empty; floor-fill will sentinel the rest
    fp = FakeProviders(table)
    result = run(run_stage3(fp, canonical=None))
    assert len(result.slide_contacts["CFO"]) == 2


# --- Stage 1 helpers ---------------------------------------------------------

def test_normalize_company_key_strips_suffixes():
    assert normalize_company_key("ACME Inc") == "acme"
    assert normalize_company_key("Acme, LLC") == "acme"
    assert normalize_company_key("Acme") == normalize_company_key("ACME Corp.")


def test_should_reconcile_on_ambiguity_or_low_confidence():
    assert should_reconcile({"needs_reconciliation": True, "confidence": 0.99})
    assert should_reconcile({"needs_reconciliation": False, "confidence": 0.5})
    assert not should_reconcile({"needs_reconciliation": False, "confidence": 0.9})


# --- Stage 2 timeout ---------------------------------------------------------

def test_with_timeout_returns_fallback_on_timeout():
    async def slow():
        await asyncio.sleep(1.0)
        return "news"

    trace = []
    out = run(with_timeout(slow(), 0.01, on_timeout={}, label="gnews", trace=trace))
    assert out == {}
    assert trace and trace[0]["outcome"] == "timed_out"


def test_with_timeout_returns_value_when_fast():
    async def fast():
        return {"articles": 3}

    out = run(with_timeout(fast(), 1.0, on_timeout={}, label="gnews"))
    assert out == {"articles": 3}
