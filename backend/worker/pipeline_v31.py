"""
Pipeline v3.1 orchestrator.

A clean, dependency-injected replacement for `process_company_profile` that
threads a JobLogger through all six stages and persists everything to the
central `profile_requests` table. Delivered as a NEW entry point — the legacy
flow in production_main.py is left intact until the gated Gamma cutover (M8).

All heavy collaborators (data providers, Council, formatter, renderer, store) are
injected, so the end-to-end wiring is unit-testable with fakes (no SDKs/network).
"""
from __future__ import annotations

from typing import Optional

from bi_resolver_io import run_stage3
from claude_formatter import council_contact_payload
from job_logger import JobLogger


async def run_pipeline_v31(
    job_id: str,
    company_data: dict,
    *,
    store,
    providers,
    council,
    formatter,
    renderer,
    logger: Optional[JobLogger] = None,
) -> dict:
    """Run Stages 1–6 for one job. Returns the result dict (also persisted).

    Stage map: 1 resolution · 2 general intel · 3 surgical contacts · 4 council ·
    5 formatter · 6 render. Each boundary updates live-progress columns; failures
    are recorded fail-loud on the job row.
    """
    canada_only = bool(company_data.get("canada_only"))
    log = logger or JobLogger(job_id, sink=store.logger_sink(job_id))

    try:
        with log:
            # Stage 1 — company resolution
            store.update_progress(job_id, stage="1_resolution", step="resolving company", progress=0.1)
            canonical = await providers.resolve_company(company_data)
            log.info("1_resolution", "resolved", "canonical company resolved",
                     {"name": canonical.name, "confidence": canonical.confidence})

            # Stage 2 — general intelligence (Canada filter does NOT apply here)
            store.update_progress(job_id, stage="2_general", step="gathering intelligence", progress=0.3,
                                  partial={"canonical": canonical.name})
            general_intel = await providers.general_intel(canonical)

            # Stage 3 — surgical per-persona contact pipeline
            store.update_progress(job_id, stage="3_contacts", step="walking persona cascades", progress=0.5)
            selection = await run_stage3(providers, canonical, canada_only=canada_only)
            log.info("3_contacts", "selected",
                     f"{selection.total_slides()} contacts across personas",
                     {"data_quality_score": selection.data_quality_score})
            store.update_progress(job_id, stage="3_contacts", step="contacts selected", progress=0.6,
                                  partial={"contact_catalogue": _serialize_catalogue(selection.contact_catalogue)})

            # Stage 4 — Council validation (only the selected slide contacts)
            store.update_progress(job_id, stage="4_council", step="validating facts", progress=0.7)
            validated = await council(general_intel, council_contact_payload(selection.slide_contacts))

            # Stage 5 — Claude formatter (authors slide copy)
            store.update_progress(job_id, stage="5_format", step="authoring slide copy", progress=0.85)
            formatted = await formatter.build(validated, selection.slide_contacts)

            # Stage 6 — PPTX render + upload
            store.update_progress(job_id, stage="6_render", step="rendering deck", progress=0.95)
            slideshow_url = await renderer.render(
                slide_contacts=selection.slide_contacts,
                company_slots=formatted["company_slots"],
                outreach_slots=formatted["outreach_slots"],
                job_id=job_id,
            )

            result = {
                "slideshow_url": slideshow_url,
                "slide_contacts": _serialize_catalogue(selection.slide_contacts),
                "contact_catalogue": _serialize_catalogue(selection.contact_catalogue),
                "enrichment_trace": selection.enrichment_trace,
                "data_quality_score": selection.data_quality_score,
                "warnings": selection.warnings,
            }
            store.persist_final(job_id, result)
            store.update_progress(job_id, stage="done", step="complete", progress=1.0)
            return result

    except Exception as exc:  # noqa: BLE001 — fail loud on the job row, re-raise
        store.fail(job_id, error_code=type(exc).__name__, error_message=str(exc))
        raise


def _serialize_catalogue(buckets: dict) -> dict:
    """StakeholderRecord -> plain dict for jsonb persistence."""
    out = {}
    for persona, records in buckets.items():
        out[persona] = [
            {
                "name": r.name, "title": r.title, "email": r.email,
                "phone": r.phone, "direct_phone": r.direct_phone, "mobile_phone": r.mobile_phone,
                "linkedin_url": r.linkedin_url, "start_date": r.start_date,
                "department": r.department, "source": r.source, "tier": r.tier,
                "proximity": r.proximity, "is_sentinel": r.is_sentinel, "marks": r.marks,
            }
            for r in records
        ]
    return out
