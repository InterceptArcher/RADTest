"""
BI Resolver — Stage 1/2/3 I/O layer (v3.1).

This module drives the *async* side of the pipeline: the surgical per-persona
cascade (Stage 3), the company-resolution decision (Stage 1), and the general-
intelligence timeout guard (Stage 2). It depends on a `Providers` seam — a bundle
of async callables wrapping ZoomInfo/Apollo/PDL/Hunter/Anthropic — injected by
the caller. No SDK is imported at module scope, so the orchestration is testable
with fakes (asyncio + stdlib) and the real adapters are wired/verified in CI.

The pure decisions (completeness, proximity ranking, systemic absence, dedupe,
floor-fill, scoring) are reused verbatim from `bi_resolver`; this module only adds
the I/O choreography around them — preserving the surgical, lazy-tier discipline.
"""
from __future__ import annotations

import asyncio
import re
from typing import Awaitable, Callable, Optional, Protocol

from bi_resolver import (
    PERSONAS, FLOOR_PRIORITY, MIN_SLIDES, ENRICH_BUDGET_PER_TIER, Proximity,
    StakeholderRecord, SelectionResult, classify_title_proximity,
    rank_by_proximity, best_proximate, systemic_field_absence,
    compute_data_quality_score, no_contact_sentinel,
)

# Cascade order. C-suite (with proximity-graded titles) → VP → Director, per
# source, ZoomInfo first. Kept deliberately small; the proximity grading inside
# the "csuite" rung covers exact/canonical/LLM-adjacent without extra API calls.
TIERS: list[tuple[str, str]] = [
    ("zoominfo", "csuite"), ("zoominfo", "vp"), ("zoominfo", "director"),
    ("apollo", "csuite"), ("apollo", "vp"), ("apollo", "director"),
    ("pdl", "csuite"), ("pdl", "vp"), ("pdl", "director"),
]

# Depth weights for the data-quality score (lower = closer/better).
_SOURCE_BASE = {"zoominfo": 0, "apollo": 5, "pdl": 10}
_KIND_OFFSET = {"csuite": 1, "vp": 3, "director": 4}


class Providers(Protocol):
    """Injected async I/O. Real impls wrap the existing clients; tests use fakes."""

    async def query(self, persona: str, source: str, kind: str,
                    canonical, canada_only: bool) -> list[StakeholderRecord]: ...

    async def judge_adjacency(self, title: str, persona: str) -> bool: ...

    async def enrich(self, record: StakeholderRecord) -> StakeholderRecord: ...

    async def fallback(self, persona: str, canonical, canada_only: bool) -> Optional[StakeholderRecord]: ...


def _trace(trace, **e):
    if trace is not None:
        trace.append(e)


def _tier_depth(source: str, kind: str) -> int:
    return _SOURCE_BASE.get(source, 15) + _KIND_OFFSET.get(kind, 4)


async def _grade_csuite_candidates(persona: str, raw: list[StakeholderRecord],
                                   providers: Providers, trace) -> list[StakeholderRecord]:
    """Assign proximity to C-suite candidates; Haiku-judge novel titles."""
    graded: list[StakeholderRecord] = []
    for r in raw:
        prox = classify_title_proximity(r.title, persona)
        if prox is None:
            ok = await providers.judge_adjacency(r.title, persona)
            if ok:
                prox = int(Proximity.LLM_ADJACENT)
            else:
                # Not an obvious proxy — but KEEP it ranked last so a real ZI
                # contact remains available as the "closest in position" floor
                # fallback (better than a web-search guess). Canonical/adjacent
                # matches still outrank it; it only wins if nothing better exists.
                r.mark("weak_title_match_kept_for_floor")
                prox = int(Proximity.UNKNOWN)
                _trace(trace, persona=persona, source=r.source, candidate_name=r.name,
                       outcome="weak_match_kept")
        r.proximity = prox
        graded.append(r)
    return graded


async def select_persona_contacts_io(
    persona: str,
    providers: Providers,
    canonical,
    canada_only: bool,
    already_used_linkedins: set[str],
    *,
    enrich_budget_per_tier: int = ENRICH_BUDGET_PER_TIER,
    trace: Optional[list] = None,
) -> tuple[list[StakeholderRecord], list[StakeholderRecord]]:
    """Async surgical cascade for one persona. Lazy across tiers, stops on qualify.

    Reuses the pure predicates from `bi_resolver` for every decision so the
    behavior matches the unit-tested selection core exactly.
    """
    selected: list[StakeholderRecord] = []
    examined: list[StakeholderRecord] = []
    zi_csuite_n: Optional[int] = None
    zi_vp_n: Optional[int] = None

    for source, kind in TIERS:
        # Mitigation 1 — short-circuit: ZI C-suite AND VP both empty -> the company
        # simply doesn't have this role senior; skip ZI Director, jump to Apollo.
        if source == "zoominfo" and kind == "director" and zi_csuite_n == 0 and zi_vp_n == 0:
            _trace(trace, persona=persona, source=source, outcome="short_circuit_skip_zi_director")
            continue

        raw = await providers.query(persona, source, kind, canonical, canada_only)
        for r in raw:
            r.source = source
            r.tier = _tier_depth(source, kind)
        if source == "zoominfo" and kind == "csuite":
            zi_csuite_n = len(raw)
        if source == "zoominfo" and kind == "vp":
            zi_vp_n = len(raw)

        if kind == "csuite":
            cands = await _grade_csuite_candidates(persona, raw, providers, trace)
        else:
            for r in raw:
                r.proximity = int(Proximity.VP if kind == "vp" else Proximity.DIRECTOR)
            cands = raw

        tier_qualified: list[StakeholderRecord] = []
        for cand in rank_by_proximity(cands)[:enrich_budget_per_tier]:
            if cand.linkedin_url and cand.linkedin_url in already_used_linkedins:
                cand.mark("duplicate_skipped")
                _trace(trace, persona=persona, source=source, candidate_name=cand.name,
                       outcome="duplicate_skipped")
                continue
            enriched = await providers.enrich(cand)
            examined.append(enriched)
            complete = enriched.is_complete()
            _trace(trace, persona=persona, source=source, candidate_name=enriched.name,
                   outcome="complete" if complete else "incomplete:" + ",".join(enriched.missing_required_fields()))
            # Only a real proximity match (exact→director) can WIN a slide in pass 1.
            # Weak/UNKNOWN-title matches stay in `examined` for floor-fill only, so we
            # never promote a complete-but-irrelevant person over the right role.
            if complete and enriched.proximity <= int(Proximity.DIRECTOR):
                tier_qualified.append(enriched)

        if tier_qualified:
            for e in tier_qualified:
                selected.append(e)
                if e.linkedin_url:
                    already_used_linkedins.add(e.linkedin_url)
            return selected, examined  # surgical stop

        missing = systemic_field_absence(examined)
        if missing:
            best = best_proximate(examined)
            if best is not None:
                best.mark(f"systemic_field_absence:{missing}")
                selected.append(best)
                if best.linkedin_url:
                    already_used_linkedins.add(best.linkedin_url)
            return selected, examined

    return selected, examined


async def run_stage3(
    providers: Providers,
    canonical,
    *,
    canada_only: bool = False,
) -> SelectionResult:
    """Full async Stage 3: per-persona cascade + global floor-fill + score."""
    slide_contacts: dict[str, list[StakeholderRecord]] = {p: [] for p in PERSONAS}
    catalogue: dict[str, list[StakeholderRecord]] = {p: [] for p in PERSONAS}
    trace: list[dict] = []
    warnings: list[str] = []
    used: set[str] = set()

    for persona in PERSONAS:
        sel, exm = await select_persona_contacts_io(
            persona, providers, canonical, canada_only, used, trace=trace)
        slide_contacts[persona] = sel
        catalogue[persona] = exm

    # Floor-fill (async, so it can call the fallback agent).
    total = sum(len(v) for v in slide_contacts.values())
    for persona in FLOOR_PRIORITY:
        if total >= MIN_SLIDES:
            break
        if slide_contacts[persona]:
            continue
        choice = best_proximate([r for r in catalogue[persona] if not r.is_sentinel])
        rung = "floor_fill_relaxed_completeness"
        if choice is None:
            choice = await providers.fallback(persona, canonical, canada_only)
            rung = "floor_fill_fallback_agent"
        if choice is None or (choice.linkedin_url and choice.linkedin_url in used):
            choice = no_contact_sentinel(persona)
            rung = "no_contact_found_for_persona"
        if not choice.is_sentinel:
            choice.mark(rung)
            if choice.linkedin_url:
                used.add(choice.linkedin_url)
        slide_contacts[persona].append(choice)
        warnings.append(f"{rung}:{persona}")
        _trace(trace, persona=persona, source=choice.source or "floor_fill", outcome=rung)
        total += 1

    return SelectionResult(
        slide_contacts=slide_contacts,
        contact_catalogue=catalogue,
        enrichment_trace=trace,
        warnings=warnings,
        data_quality_score=compute_data_quality_score(slide_contacts),
    )


# ---------------------------------------------------------------------------
# Stage 1 — company-resolution decision helpers (pure)
# ---------------------------------------------------------------------------

_SUFFIXES = ("inc", "llc", "corp", "ltd", "limited", "co", "pte", "gmbh", "plc", "sa", "ag")


def normalize_company_key(name: str) -> str:
    """Cache-key normalization (Mitigation 9): lowercase, strip legal suffixes."""
    n = (name or "").lower().strip()
    n = re.sub(r"[.,]", " ", n)
    tokens = [t for t in n.split() if t not in _SUFFIXES]
    return " ".join(tokens).strip()


def should_reconcile(haiku_output: dict, *, confidence_floor: float = 0.7) -> bool:
    """Trigger Claude web-search reconciliation on ambiguity OR low confidence."""
    if haiku_output.get("needs_reconciliation"):
        return True
    return float(haiku_output.get("confidence", 0.0)) < confidence_floor


# ---------------------------------------------------------------------------
# Stage 2 — general-intelligence timeout guard
# ---------------------------------------------------------------------------

async def with_timeout(coro: Awaitable, seconds: float, *, on_timeout, label: str,
                       trace: Optional[list] = None):
    """Run `coro` with a hard timeout (Mitigation 11 for GNews). On timeout return
    `on_timeout` and record it in the trace instead of blocking the stage."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        _trace(trace, source=label, outcome="timed_out")
        return on_timeout
