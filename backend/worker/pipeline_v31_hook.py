"""
Flag-gated v3.1 integration hook.

`run_v31_pipeline` is the production entry the monolith calls when
USE_V31_PIPELINE=true: it runs the new surgical Stage-3 contacts + the exact-copy
PPTX render, mutating `validated_data` so the existing result/dashboard carry the
new contact catalogue, quality score, and deck URL. The legacy intel/council
stages are untouched — only contacts + slideshow are swapped (matching the design
intent). On ANY failure it raises, so the caller falls back to the Gamma path.

`assemble_v31` is the dependency-injected core (no SDKs/network) and is unit-tested
with fakes; the prod wiring (real clients, template download, storage upload) runs
only under the flag and is validated on the first prod job.
"""
from __future__ import annotations

import os
import sys
import tempfile
import logging
from typing import Optional

# Ensure the worker dir is importable whether this is loaded as `worker.pipeline_v31_hook`
# (prod, from production_main) or bare (tests) — the v3.1 modules use bare imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bi_resolver_io import run_stage3

logger = logging.getLogger(__name__)


def _serialize(buckets: dict) -> dict:
    out = {}
    for persona, records in buckets.items():
        out[persona] = [{
            "name": r.name, "title": r.title, "email": r.email,
            "phone": r.phone, "direct_phone": r.direct_phone, "mobile_phone": r.mobile_phone,
            "linkedin_url": r.linkedin_url, "start_date": r.start_date, "department": r.department,
            "source": r.source, "tier": r.tier, "proximity": r.proximity,
            "is_sentinel": r.is_sentinel, "marks": r.marks,
        } for r in records]
    return out


async def assemble_v31(providers, formatter, renderer, canonical, validated_facts: dict,
                       job_id: str, canada_only: bool = False) -> dict:
    """Stage 3 (surgical contacts) + Stage 5/6 (author + render). Pure of I/O
    specifics — all collaborators injected. Returns {selection, slideshow_url}."""
    selection = await run_stage3(providers, canonical, canada_only=canada_only)
    company_tokens = renderer.introspect_company_tokens()
    formatted = await formatter.build(validated_facts, company_tokens, selection.slide_contacts)
    slideshow_url = await renderer.render(
        slide_contacts=selection.slide_contacts,
        company_slots=formatted["company_slots"],
        outreach_slots=formatted["outreach_slots"],
        job_id=job_id,
    )
    return {"selection": selection, "slideshow_url": slideshow_url}


def _make_storage_uploader(base: str):
    """Returns uploader(local_path, storage_key) -> public_url using the service key."""
    import httpx
    key = os.environ["SUPABASE_KEY"]  # must be service_role for writes

    def upload(local_path: str, storage_key: str) -> str:
        with open(local_path, "rb") as f:
            data = f.read()
        resp = httpx.post(
            f"{base}/storage/v1/object/{storage_key}",
            content=data,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "x-upsert": "true",
                "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            },
            timeout=90,
        )
        resp.raise_for_status()
        return f"{base}/storage/v1/object/public/{storage_key}"

    return upload


async def run_v31_pipeline(company_data: dict, validated_data: dict, job_id: str,
                           jobs_store: Optional[dict] = None) -> dict:
    """Production entry. Raises on failure (caller falls back to Gamma)."""
    import httpx
    from zoominfo_client import ZoomInfoClient
    from providers_live import LiveProviders
    from claude_formatter import ClaudeFormatter
    from pptx_renderer import PptxRenderer
    from bi_resolver import CanonicalCompany

    canonical = CanonicalCompany(
        name=validated_data.get("company_name") or company_data.get("company_name", ""),
        primary_domain=validated_data.get("domain") or company_data.get("domain", ""),
        industry=validated_data.get("industry", ""),
    )

    base = os.environ["SUPABASE_URL"].rstrip("/")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET_DECKS", "decks")
    master_url = f"{base}/storage/v1/object/public/{bucket}/master-template.pptx"

    # Download the master template to a temp file for python-pptx.
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(master_url)
        r.raise_for_status()
        tmp.write(r.content)
    tmp.flush(); tmp.close()

    providers = LiveProviders(zi_client=ZoomInfoClient())
    formatter = ClaudeFormatter()
    renderer = PptxRenderer(tmp.name, uploader=_make_storage_uploader(base))

    # --- Stage 3: surgical contacts (validated, reliable). Persist FIRST, so a
    # render failure below still leaves the 6-bucket catalogue + score on the job.
    sel = await run_stage3(providers, canonical, canada_only=bool(company_data.get("canada_only")))
    validated_data["slide_contacts"] = _serialize(sel.slide_contacts)
    validated_data["contact_catalogue"] = _serialize(sel.contact_catalogue)
    validated_data["data_quality_score"] = sel.data_quality_score
    validated_data["enrichment_trace"] = sel.enrichment_trace
    logger.info("v3.1 contacts: %d across personas, dqs=%.2f",
                sum(len(v) for v in sel.slide_contacts.values()), sel.data_quality_score)

    # --- Stage 5/6: author + render the deck. If this raises, the caller catches
    # it, records the error, and falls back to the Gamma deck — but the contacts
    # above are already on the job (so the dashboard shows them either way).
    company_tokens = renderer.introspect_company_tokens()
    formatted = await formatter.build(validated_data, company_tokens, sel.slide_contacts)
    url = await renderer.render(
        slide_contacts=sel.slide_contacts,
        company_slots=formatted["company_slots"],
        outreach_slots=formatted["outreach_slots"],
        job_id=job_id,
    )
    validated_data["slideshow_url"] = url
    logger.info("v3.1 deck rendered: %s", url)
    return {
        "success": True,
        "slideshow_url": url,
        "slideshow_id": job_id,
        "slideshow_status": "completed",
        "data_quality_score": sel.data_quality_score,
    }
