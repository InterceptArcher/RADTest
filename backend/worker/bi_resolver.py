"""
BI Resolver — v3.1 surgical contact pipeline (core selection logic).

This module hosts the *pure* heart of Stage 3 from the RAD pipeline restructure
(see docs/superpowers/specs/2026-05-26-rad-pipeline-restructure-design.md). The
I/O-bound stage adapters (ZoomInfo/Apollo/PDL/Hunter queries, Haiku LinkedIn
enrichment, the Stage-3 fallback agent, Supabase persistence) are layered on top
in later milestones; everything in THIS file is deterministic, dependency-free,
and unit-testable without network or external SDKs.

Core philosophy (do not regress): we are surgical, not a bulk-pull-then-sort
swarm. For each of the six personas we walk a proximity-ordered cascade LAZILY,
tier by tier, and point enrichment at only the closest few candidates. We descend
a tier only to *find* the right person — never to accumulate slides. "Uncapped"
means: when more than one co-equal, high-proximity candidate at the single winning
tier independently clears the completeness bar, each earns a slide. The moment a
tier qualifies, we stop descending.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Iterable, Optional

# ---------------------------------------------------------------------------
# Persona model (v3.1 — six personas, from the master template's slide 7)
# ---------------------------------------------------------------------------

# Discovery/slide order. Floor-fill uses a different (reliability) order below.
PERSONAS: list[str] = ["CIO", "CTO", "CFO", "COO", "CISO", "CPO"]

# Order used only by the floor-fill pass when fewer than MIN_SLIDES qualify.
# The original four anchor the floor; CISO/CPO are least likely to exist at
# smaller / non-tech companies, so they fill last.
FLOOR_PRIORITY: list[str] = ["CTO", "CIO", "CFO", "COO", "CISO", "CPO"]

MIN_SLIDES = 4                 # the deck floor; above this the count is uncapped
ENRICH_BUDGET_PER_TIER = 5     # surgical cap — enrich the closest few, not the pool

# Required for a contact to earn a slide. `phone` is intentionally NOT required
# (Session-2 decision: "the only value that can be missing is a phone number").
REQUIRED_FIELDS: tuple[str, ...] = ("name", "title", "email", "linkedin_url", "start_date")

# Source reliability weights for the data-quality score.
SOURCE_RELIABILITY: dict[str, float] = {
    "zoominfo": 1.0,
    "apollo": 0.85,
    "pdl": 0.7,
    "hunter": 0.5,
    "web_search": 0.4,
    "agent": 0.4,
    "": 0.0,
}

# Canonical title buckets per persona. `exact` is the literal C-suite title;
# `adjacent` are accepted proxies. Titles not matched here fall through to the
# Haiku adjacency judge in the I/O layer (proximity returned as None).
# CPO == Chief PRODUCT Officer (template frames personas by finance/ops/tech
# decision-drivers — product axis, NOT Chief People Officer).
PERSONA_TITLE_BUCKETS: dict[str, dict[str, object]] = {
    "CIO": {
        "exact": "chief information officer",
        "adjacent": {
            "chief digital officer", "chief digital information officer",
            "vp of it", "vp information technology", "head of it",
            "vp of information systems", "svp information technology",
            "global cio", "group cio",
        },
    },
    "CTO": {
        "exact": "chief technology officer",
        "adjacent": {
            "chief engineering officer", "chief technical officer",
            "vp of engineering", "vp of technology", "head of engineering",
            "head of technology", "svp engineering", "evp technology",
        },
    },
    "CFO": {
        "exact": "chief financial officer",
        "adjacent": {
            "vp of finance", "head of finance", "svp finance",
            "treasurer", "controller", "vp finance & operations",
            "chief accounting officer",
        },
    },
    "COO": {
        "exact": "chief operating officer",
        "adjacent": {
            "chief operations officer", "vp of operations", "head of operations",
            "svp operations", "general manager", "gm", "chief business officer",
        },
    },
    "CISO": {
        "exact": "chief information security officer",
        "adjacent": {
            "chief security officer", "vp of security", "vp of information security",
            "head of cybersecurity", "head of information security", "head of infosec",
            "vp cyber security", "ciso", "deputy ciso",
        },
    },
    "CPO": {
        "exact": "chief product officer",
        "adjacent": {
            "vp of product", "head of product", "svp product",
            "vp product management", "evp product", "chief product & technology officer",
        },
    },
}


class Proximity(IntEnum):
    """Lower = closer to the persona. Used to order candidates within a tier."""
    EXACT = 0          # literal C-suite title for the persona
    CANONICAL = 1      # in the persona's curated adjacent set
    LLM_ADJACENT = 2   # judged a reasonable proxy by the Haiku adjacency call
    VP = 3             # VP-tier role-area match
    DIRECTOR = 4       # Director-tier role-area match
    UNKNOWN = 9        # fallback / agent-sourced


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation/extra space — for robust title comparison."""
    t = (title or "").lower().strip()
    t = t.replace("&", "and")
    t = re.sub(r"[.,/()]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def classify_title_proximity(title: str, persona: str) -> Optional[int]:
    """Return a Proximity for a title against a persona, or None if undecidable.

    None signals the I/O layer to fall back to the Haiku adjacency judge — we do
    NOT guess. This keeps the canonical fast-path auditable while still handling
    novel titles (e.g. "Chief Code Officer") gracefully one layer up.
    """
    bucket = PERSONA_TITLE_BUCKETS.get(persona)
    if not bucket:
        return None
    norm = _normalize_title(title)
    if not norm:
        return None
    if norm == bucket["exact"]:
        return int(Proximity.EXACT)
    if norm in bucket["adjacent"]:  # type: ignore[operator]
        return int(Proximity.CANONICAL)
    return None


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class StakeholderRecord:
    """One candidate/selected contact for a persona slide.

    Mirrors the master template's contact-slide fields (slide 8). `marks` records
    every degraded-path note for the dashboard trace (no silent failures).
    """
    persona: str
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    direct_phone: str = ""
    mobile_phone: str = ""
    linkedin_url: str = ""
    start_date: str = ""
    department: str = ""
    about: str = ""
    strategic_priorities: list[str] = field(default_factory=list)
    conversation_starters: str = ""
    communication_preference: str = ""
    source: str = ""
    person_id: str = ""          # ZoomInfo contact id — for the final enrich pass
    tier: int = 1
    proximity: int = int(Proximity.UNKNOWN)
    # Set of sources that independently agreed on this contact's email — drives
    # the cross_source_agreement term of the data-quality score.
    email_sources: set[str] = field(default_factory=set)
    is_sentinel: bool = False
    marks: list[str] = field(default_factory=list)

    def mark(self, note: str) -> None:
        if note not in self.marks:
            self.marks.append(note)

    def missing_required_fields(self) -> list[str]:
        missing = []
        for f in REQUIRED_FIELDS:
            if not str(getattr(self, f, "") or "").strip():
                missing.append(f)
        return missing

    def is_complete(self) -> bool:
        return not self.is_sentinel and not self.missing_required_fields()


@dataclass
class CanonicalCompany:
    name: str
    primary_domain: str = ""
    industry: str = ""
    hq_country: str = ""
    employee_bucket: str = ""
    is_subsidiary: bool = False
    confidence: float = 0.0
    decision_basis: str = ""


@dataclass
class Tier:
    """One rung of a persona's cascade: a source + its candidate list at a tier."""
    tier: int
    source: str
    candidates: list[StakeholderRecord]


@dataclass
class SelectionResult:
    """Output of the pure contact-selection pass."""
    slide_contacts: dict[str, list[StakeholderRecord]]   # persona -> selected (>=0)
    contact_catalogue: dict[str, list[StakeholderRecord]]  # persona -> all examined
    enrichment_trace: list[dict]
    warnings: list[str]
    data_quality_score: float = 0.0

    def flat_slide_contacts(self) -> list[StakeholderRecord]:
        """Selected contacts flattened in persona order, then by proximity."""
        out: list[StakeholderRecord] = []
        for persona in PERSONAS:
            out.extend(rank_by_proximity(self.slide_contacts.get(persona, [])))
        return out

    def total_slides(self) -> int:
        return sum(len(v) for v in self.slide_contacts.values())


def no_contact_sentinel(persona: str) -> StakeholderRecord:
    rec = StakeholderRecord(persona=persona, name="No contact found", is_sentinel=True, source="")
    rec.mark("no_contact_found_for_persona")
    return rec


# ---------------------------------------------------------------------------
# Pure selection logic
# ---------------------------------------------------------------------------

def rank_by_proximity(records: list[StakeholderRecord]) -> list[StakeholderRecord]:
    """Closest first: lower proximity, then shallower tier, then fewer gaps."""
    return sorted(
        records,
        key=lambda r: (r.proximity, r.tier, len(r.missing_required_fields()), r.name),
    )


def best_proximate(records: list[StakeholderRecord]) -> Optional[StakeholderRecord]:
    if not records:
        return None
    return rank_by_proximity(records)[0]


def systemic_field_absence(examined: list[StakeholderRecord]) -> Optional[str]:
    """If one required field is missing across ALL examined candidates, return it.

    Mitigation 4: a company-level data gap (e.g. obfuscated emails everywhere)
    rather than a per-candidate miss — so we stop walking instead of burning the
    whole cascade chasing a field nobody publishes.
    """
    real = [r for r in examined if not r.is_sentinel]
    if not real:
        return None
    for f in REQUIRED_FIELDS:
        if all(not str(getattr(r, f, "") or "").strip() for r in real):
            return f
    return None


def _trace(trace: Optional[list], **entry) -> None:
    if trace is not None:
        trace.append(entry)


def select_persona_contacts(
    persona: str,
    tiers: Iterable[Tier],
    enrich: Callable[[StakeholderRecord], StakeholderRecord],
    already_used_linkedins: set[str],
    *,
    enrich_budget_per_tier: int = ENRICH_BUDGET_PER_TIER,
    trace: Optional[list] = None,
) -> tuple[list[StakeholderRecord], list[StakeholderRecord]]:
    """Walk one persona's cascade lazily and return (selected, examined).

    `tiers` is consumed as an iterator; once a tier qualifies we return without
    advancing it further, so the caller's generator never queries weaker tiers /
    other sources. This is where "stop descending" is enforced mechanically.
    """
    selected: list[StakeholderRecord] = []
    examined: list[StakeholderRecord] = []

    for tier in tiers:
        ranked = rank_by_proximity(tier.candidates)[:enrich_budget_per_tier]
        tier_qualified: list[StakeholderRecord] = []
        for cand in ranked:
            if cand.linkedin_url and cand.linkedin_url in already_used_linkedins:
                cand.mark("duplicate_skipped")
                _trace(trace, persona=persona, tier=tier.tier, source=tier.source,
                       candidate_name=cand.name, outcome="duplicate_skipped")
                continue
            enriched = enrich(cand)
            examined.append(enriched)
            complete = enriched.is_complete()
            _trace(trace, persona=persona, tier=tier.tier, source=tier.source,
                   candidate_name=enriched.name,
                   outcome="complete" if complete else "incomplete:" + ",".join(enriched.missing_required_fields()))
            if complete:
                tier_qualified.append(enriched)

        if tier_qualified:
            # Surgical stop: the strongest tier that yields any complete contact
            # wins. Promote every co-equal qualifier from THIS tier, then stop.
            for e in tier_qualified:
                selected.append(e)
                if e.linkedin_url:
                    already_used_linkedins.add(e.linkedin_url)
            return selected, examined

        missing = systemic_field_absence(examined)
        if missing:
            best = best_proximate(examined)
            if best is not None:
                best.mark(f"systemic_field_absence:{missing}")
                selected.append(best)
                if best.linkedin_url:
                    already_used_linkedins.add(best.linkedin_url)
                _trace(trace, persona=persona, tier=tier.tier, source=tier.source,
                       candidate_name=best.name, outcome=f"accepted_systemic_absence:{missing}")
            return selected, examined

    return selected, examined  # cascade exhausted with nothing complete


def floor_fill(
    slide_contacts: dict[str, list[StakeholderRecord]],
    contact_catalogue: dict[str, list[StakeholderRecord]],
    already_used_linkedins: set[str],
    *,
    fallback_agent: Optional[Callable[[str], Optional[StakeholderRecord]]] = None,
    trace: Optional[list] = None,
) -> list[str]:
    """Guarantee >= MIN_SLIDES by relaxing the bar on priority personas.

    Runs once, globally, after the per-persona pass. Returns warnings. Personas
    that already contributed a slide are left untouched — we never pad a persona
    that's already represented.
    """
    warnings: list[str] = []
    total = sum(len(v) for v in slide_contacts.values())

    for persona in FLOOR_PRIORITY:
        if total >= MIN_SLIDES:
            break
        if slide_contacts.get(persona):
            continue

        # Rung 2: best-proximate incomplete candidate we already examined.
        choice = best_proximate(
            [r for r in contact_catalogue.get(persona, []) if not r.is_sentinel]
        )
        rung = "floor_fill_relaxed_completeness"

        # Rung 3: agentic "any senior person" search.
        if choice is None and fallback_agent is not None:
            choice = fallback_agent(persona)
            rung = "floor_fill_fallback_agent"

        # Rung 4: the slide still ships, marked "no contact found".
        if choice is None:
            choice = no_contact_sentinel(persona)
            rung = "no_contact_found_for_persona"

        if choice.linkedin_url and choice.linkedin_url in already_used_linkedins:
            # Don't floor-fill with someone already headlining another slide.
            choice = no_contact_sentinel(persona)
            rung = "no_contact_found_for_persona"

        if not choice.is_sentinel:
            choice.mark(rung)
        if choice.linkedin_url:
            already_used_linkedins.add(choice.linkedin_url)
        slide_contacts.setdefault(persona, []).append(choice)
        warnings.append(f"{rung}:{persona}")
        _trace(trace, persona=persona, tier=0, source=choice.source or "floor_fill",
               candidate_name=choice.name, outcome=rung)
        total += 1

    return warnings


def compute_data_quality_score(slide_contacts: dict[str, list[StakeholderRecord]]) -> float:
    """Weighted 0..1 score, averaged over the N selected contacts (v3.1).

    Bigger decks do NOT score higher for size — the score is a mean, so the
    floor-filled / incomplete contacts that only exist to satisfy MIN_SLIDES pull
    the average down, exactly as they should. Persona coverage is intentionally
    not a term here.
    """
    contacts = [c for v in slide_contacts.values() for c in v]
    if not contacts:
        return 0.0

    reliability = sum(SOURCE_RELIABILITY.get(c.source, 0.0) for c in contacts) / len(contacts)

    avg_tier = sum(max(1, c.tier) for c in contacts) / len(contacts)
    cascade_efficiency = max(0.0, min(1.0, 1.0 - (avg_tier - 1) * 0.15))

    coverage = sum(
        (len(REQUIRED_FIELDS) - len(c.missing_required_fields())) / len(REQUIRED_FIELDS)
        for c in contacts
    ) / len(contacts)

    agreement = sum(1 for c in contacts if len(c.email_sources) >= 2) / len(contacts)

    score = 0.4 * reliability + 0.3 * cascade_efficiency + 0.2 * coverage + 0.1 * agreement
    return round(max(0.0, min(1.0, score)), 4)


def quality_band(score: float) -> str:
    """Provisional thresholds (tunable): High >= 0.75, Medium 0.4-0.75, Low < 0.4."""
    if score >= 0.75:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"


def run_contact_selection(
    persona_tiers: dict[str, Iterable[Tier]],
    enrich: Callable[[StakeholderRecord], StakeholderRecord],
    *,
    fallback_agent: Optional[Callable[[str], Optional[StakeholderRecord]]] = None,
) -> SelectionResult:
    """Pure orchestration of the full Stage-3 selection.

    `persona_tiers[persona]` is a (lazy) iterable of Tier rungs produced by the
    I/O layer; `enrich` and `fallback_agent` are injected so this stays testable
    with no network. Returns the assembled slide contacts + catalogue + trace +
    data-quality score.
    """
    slide_contacts: dict[str, list[StakeholderRecord]] = {p: [] for p in PERSONAS}
    contact_catalogue: dict[str, list[StakeholderRecord]] = {p: [] for p in PERSONAS}
    enrichment_trace: list[dict] = []
    warnings: list[str] = []
    already_used: set[str] = set()

    # Pass 1 — per-persona surgical discovery + enrichment.
    for persona in PERSONAS:
        tiers = persona_tiers.get(persona, [])
        selected, examined = select_persona_contacts(
            persona, tiers, enrich, already_used, trace=enrichment_trace
        )
        slide_contacts[persona] = selected
        contact_catalogue[persona] = examined

    # Pass 2 — floor-fill so the deck always has >= MIN_SLIDES.
    warnings.extend(
        floor_fill(slide_contacts, contact_catalogue, already_used,
                   fallback_agent=fallback_agent, trace=enrichment_trace)
    )

    score = compute_data_quality_score(slide_contacts)
    return SelectionResult(
        slide_contacts=slide_contacts,
        contact_catalogue=contact_catalogue,
        enrichment_trace=enrichment_trace,
        warnings=warnings,
        data_quality_score=score,
    )
