"""
Unit tests for the pure Stage-3 selection core (`worker/bi_resolver.py`).

These cover the v3.1 cardinality change and — critically — the surgical-discipline
guardrails: lazy tier descent, co-equal promotion, stop-descending, cross-slide
dedupe, systemic-absence, floor-fill, and the average-not-sum data-quality score.
No network or external SDKs required.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bi_resolver import (  # noqa: E402
    PERSONAS, FLOOR_PRIORITY, MIN_SLIDES, ENRICH_BUDGET_PER_TIER, Proximity,
    StakeholderRecord, Tier, classify_title_proximity, select_persona_contacts,
    floor_fill, compute_data_quality_score, quality_band, run_contact_selection,
    no_contact_sentinel,
)

IDENTITY = lambda r: r  # noqa: E731  candidates are pre-filled in these tests


def make_rec(persona, name="X", proximity=0, tier=1, source="zoominfo",
             linkedin=None, complete=True, email_sources=2, missing=()):
    ln = linkedin if linkedin is not None else f"https://linkedin.com/in/{name.lower()}"
    r = StakeholderRecord(
        persona=persona, name=name, title="Some Title",
        email=f"{name.lower()}@acme.com", linkedin_url=ln, start_date="2024-01",
        proximity=proximity, tier=tier, source=source,
    )
    if not complete:
        r.email, r.start_date = "", ""
    for f in missing:
        setattr(r, f, "" if f != "strategic_priorities" else [])
    if email_sources:
        r.email_sources = set("abcdefg"[:email_sources])
    return r


# --- persona model ----------------------------------------------------------

def test_six_personas_and_floor_priority():
    assert PERSONAS == ["CIO", "CTO", "CFO", "COO", "CISO", "CPO"]
    assert sorted(FLOOR_PRIORITY) == sorted(PERSONAS)
    assert FLOOR_PRIORITY[:4] == ["CTO", "CIO", "CFO", "COO"]  # originals anchor floor
    assert MIN_SLIDES == 4


def test_cpo_is_product_not_people():
    assert classify_title_proximity("Chief Product Officer", "CPO") == int(Proximity.EXACT)
    assert classify_title_proximity("VP of Product", "CPO") == int(Proximity.CANONICAL)
    assert classify_title_proximity("Chief People Officer", "CPO") is None  # NOT a match


def test_title_proximity_exact_canonical_unknown():
    assert classify_title_proximity("chief technology officer", "CTO") == int(Proximity.EXACT)
    assert classify_title_proximity("VP of Engineering", "CTO") == int(Proximity.CANONICAL)
    assert classify_title_proximity("Chief Code Officer", "CTO") is None  # -> Haiku judge


def test_completeness_phone_optional():
    r = make_rec("CTO")
    r.phone = ""
    assert r.is_complete()              # phone missing is fine
    r.email = ""
    assert not r.is_complete()
    assert "email" in r.missing_required_fields()


# --- surgical discipline -----------------------------------------------------

def test_lazy_descent_does_not_query_weaker_tiers():
    consumed = []

    def gen():
        consumed.append(1)
        yield Tier(1, "zoominfo", [make_rec("CTO", "Alice")])
        consumed.append(2)  # must never run — tier 1 qualified
        yield Tier(4, "zoominfo", [make_rec("CTO", "Bob")])

    selected, _ = select_persona_contacts("CTO", gen(), IDENTITY, set())
    assert [r.name for r in selected] == ["Alice"]
    assert consumed == [1], "weaker tier was produced despite tier 1 qualifying"


def test_co_equal_qualifiers_each_get_a_slide():
    tier = Tier(1, "zoominfo", [make_rec("CFO", "A", proximity=0), make_rec("CFO", "B", proximity=0)])
    selected, _ = select_persona_contacts("CFO", [tier], IDENTITY, set())
    assert {r.name for r in selected} == {"A", "B"}


def test_uncapped_three_complete_three_slides():
    tier = Tier(1, "zoominfo", [make_rec("CIO", n) for n in ("A", "B", "C")])
    selected, _ = select_persona_contacts("CIO", [tier], IDENTITY, set())
    assert len(selected) == 3


def test_stop_descending_ignores_deeper_complete_candidates():
    tiers = [
        Tier(1, "zoominfo", [make_rec("CTO", "Exact")]),
        Tier(4, "zoominfo", [make_rec("CTO", "Vp1"), make_rec("CTO", "Vp2")]),
    ]
    selected, _ = select_persona_contacts("CTO", iter(tiers), IDENTITY, set())
    assert [r.name for r in selected] == ["Exact"]  # never reached the VP tier


def test_cross_slide_dedupe_skips_repeat_linkedin():
    used = set()
    s1, _ = select_persona_contacts(
        "CIO", [Tier(1, "zoominfo", [make_rec("CIO", "Dana", linkedin="https://li/dana")])], IDENTITY, used)
    s2, _ = select_persona_contacts(
        "CTO", [Tier(1, "zoominfo", [make_rec("CTO", "Dana2", linkedin="https://li/dana")])], IDENTITY, used)
    assert len(s1) == 1 and s2 == []  # same LinkedIn -> not duplicated as a slide


def test_enrich_budget_caps_enrichment_per_tier():
    calls = {"n": 0}

    def counting_enrich(r):
        calls["n"] += 1
        return r

    # 10 candidates all missing start_date -> systemic absence, but only top-5 enriched.
    cands = [make_rec("COO", f"P{i}", complete=False) for i in range(10)]
    for c in cands:
        c.email = "x@acme.com"  # only start_date missing -> systemic on start_date
    selected, examined = select_persona_contacts("COO", [Tier(4, "apollo", cands)], counting_enrich, set())
    assert calls["n"] == ENRICH_BUDGET_PER_TIER
    assert len(selected) == 1 and "systemic_field_absence:start_date" in selected[0].marks


# --- floor fill --------------------------------------------------------------

def test_floor_fill_reaches_minimum_with_priority():
    slide = {p: [] for p in PERSONAS}
    slide["CTO"] = [make_rec("CTO", "Real1")]
    slide["CFO"] = [make_rec("CFO", "Real2")]
    catalogue = {p: [] for p in PERSONAS}
    # CIO/COO have incomplete candidates available to relax onto.
    catalogue["CIO"] = [make_rec("CIO", "Inc1", complete=False)]
    catalogue["COO"] = [make_rec("COO", "Inc2", complete=False)]
    warns = floor_fill(slide, catalogue, set())
    total = sum(len(v) for v in slide.values())
    assert total == MIN_SLIDES
    assert slide["CTO"][0].name == "Real1"  # represented persona untouched
    assert any("CIO" in w for w in warns) and any("COO" in w for w in warns)


def test_floor_fill_uses_fallback_then_sentinel():
    slide = {p: [] for p in PERSONAS}
    slide["CTO"] = [make_rec("CTO", "R1")]
    slide["CFO"] = [make_rec("CFO", "R2")]
    slide["CIO"] = [make_rec("CIO", "R3")]
    catalogue = {p: [] for p in PERSONAS}  # nothing examined for the 4th

    def fallback(persona):
        return make_rec(persona, "AgentFound", source="agent")

    warns = floor_fill(slide, catalogue, set(), fallback_agent=fallback)
    assert sum(len(v) for v in slide.values()) == MIN_SLIDES
    assert any("fallback_agent" in w for w in warns)

    # With no fallback and empty catalogue -> sentinel, slide still ships.
    slide2 = {p: [] for p in PERSONAS}
    slide2["CTO"] = [make_rec("CTO", "R1")]
    warns2 = floor_fill(slide2, {p: [] for p in PERSONAS}, set())
    flat = [c for v in slide2.values() for c in v]
    assert len(flat) >= MIN_SLIDES
    assert any(c.is_sentinel for c in flat)


# --- data quality score ------------------------------------------------------

def test_dqs_perfect_deck_is_high():
    slide = {"CTO": [make_rec("CTO", "A")], "CIO": [make_rec("CIO", "B")],
             "CFO": [make_rec("CFO", "C")], "COO": [make_rec("COO", "D")]}
    score = compute_data_quality_score(slide)
    assert score == 1.0 and quality_band(score) == "High"


def test_dqs_is_average_not_sum():
    strong = {"CTO": [make_rec("CTO", "A")], "CIO": [make_rec("CIO", "B")],
              "CFO": [make_rec("CFO", "C")], "COO": [make_rec("COO", "D")]}
    score_strong = compute_data_quality_score(strong)
    bigger = dict(strong)
    bigger["CISO"] = [no_contact_sentinel("CISO")]
    bigger["CPO"] = [no_contact_sentinel("CPO")]
    score_bigger = compute_data_quality_score(bigger)
    assert score_bigger < score_strong  # padding the deck lowers the average


def test_quality_bands():
    assert quality_band(0.9) == "High"
    assert quality_band(0.5) == "Medium"
    assert quality_band(0.2) == "Low"


# --- end to end (pure) -------------------------------------------------------

def test_run_contact_selection_end_to_end():
    persona_tiers = {
        "CIO": [Tier(1, "zoominfo", [make_rec("CIO", "Ivy")])],
        "CTO": [Tier(1, "zoominfo", [make_rec("CTO", "Tom"), make_rec("CTO", "Tina")])],
        "CFO": [Tier(1, "zoominfo", [make_rec("CFO", "Fred")])],
        "COO": [],            # no candidates
        "CISO": [],
        "CPO": [],
    }
    result = run_contact_selection(persona_tiers, IDENTITY)
    assert result.total_slides() >= MIN_SLIDES
    assert len(result.slide_contacts["CTO"]) == 2  # co-equal -> 2 slides
    assert result.enrichment_trace, "trace should record cascade steps"
    assert 0.0 <= result.data_quality_score <= 1.0
    # flattened slide order follows PERSONAS order
    personas_in_order = [c.persona for c in result.flat_slide_contacts()]
    assert personas_in_order == sorted(personas_in_order, key=PERSONAS.index)
