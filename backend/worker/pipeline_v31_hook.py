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
# backend/ too, so we can import content_audit (lives at the backend root).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


_COLLATERAL_TOKENS = [
    "[Future-proof your IT for anywhere work]",
    "[HP Workforce Experience Platform: Windows 11 Readiness]",
    "[High-performance power from anywhere]",
    "[Maximize productivity with AI workstation laptops]",
]
_COLLATERAL_STEPS = [
    "Build awareness and credibility", "Frame business challenges",
    "Demonstrate proven outcomes", "Enable decision-making",
]
_SUPPORTING_ASSET_TOKEN = "[Maximize productivity with AI workstation laptops]"

# Deterministic department per persona role (the master leaves it blank and ZI
# often omits it). The persona IS the role, so the function is unambiguous:
# the three technology roles sit in IT, finance in Finance, ops in Operations,
# product in Product.
DEPARTMENT_BY_PERSONA = {
    "CIO": "Information Technology",
    "CTO": "Information Technology",
    "CISO": "Information Technology",
    "CFO": "Finance",
    "COO": "Operations",
    "CPO": "Product",
}


def _parse_employee_count(raw) -> Optional[int]:
    if raw is None:
        return None
    try:
        return int(str(raw).replace(",", "").replace("+", "").split("-")[0].strip())
    except (ValueError, TypeError):
        return None


def _parse_revenue(raw) -> Optional[float]:
    """Best-effort numeric revenue from strings like '$198.3 billion' / '$50M-$100M'
    (takes the first/low number) → absolute dollars, or None."""
    if raw is None:
        return None
    import re
    s = str(raw).lower().replace(",", "").replace("$", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    num = float(m.group(1))
    if "billion" in s or "bn" in s or re.search(r"\bb\b", s):
        num *= 1_000_000_000
    elif "million" in s or "mn" in s or re.search(r"\bm\b", s):
        num *= 1_000_000
    elif "k" in s:
        num *= 1_000
    return num if num > 0 else None


def _fmt_spend_range(low: float, high: float) -> str:
    def one(v: float) -> str:
        if v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.1f}B"
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        return f"${v / 1_000:.0f}K"
    return f"{one(low)} – {one(high)} annually"


def estimate_it_spend(facts: dict) -> str:
    """Resolve the Executive-Snapshot IT-spend for the factual token.

    The council emits this under several keys (and sometimes not at all), so we
    check every known variant top-level AND nested under `executive_snapshot`,
    then fall back to computing from employee count ($10K–$20K/employee — mirrors
    the dashboard's `_build_executive_snapshot`) or revenue (IT spend ≈ 3–5% of
    revenue). Returns '' only when there's genuinely nothing to estimate from."""
    es = facts.get("executive_snapshot") or {}
    for src in (facts, es):
        for key in ("estimated_it_spend", "estimated_it_spend_display", "estimated_it_spend_range", "it_spend"):
            v = src.get(key)
            if v and str(v).strip():
                return str(v).strip()
    emp = _parse_employee_count(facts.get("employee_count") or es.get("employee_count"))
    if emp:
        return _fmt_spend_range(emp * 10_000, emp * 20_000)
    rev = _parse_revenue(facts.get("annual_revenue") or es.get("annual_revenue")
                         or facts.get("revenue") or es.get("revenue"))
    if rev:
        return _fmt_spend_range(rev * 0.03, rev * 0.05)
    return ""


def _content_audit_links(validated_data: dict, canonical, slide_contacts: dict):
    """Return (collateral hyperlink_slots, per-persona outreach_hyperlinks).

    Maps each Recommended-Sales-Program collateral slot + each persona's supporting
    asset to a real content-audit document (asset name hyperlinked to its DAM URL).
    Best-effort: returns whatever it can match; never raises into the pipeline.
    """
    hyperlink_slots: dict = {}
    outreach_hyperlinks: dict = {}
    try:
        import content_audit
        content_audit.load_content_audit()
        industry = validated_data.get("industry", "") or getattr(canonical, "industry", "")
        bs = validated_data.get("buying_signals") or {}
        topics = bs.get("intent_topics") or [
            t.get("topic") for t in (bs.get("intent_topics_detailed") or []) if t.get("topic")]
        topic = topics[0] if topics else ""

        def _link(item):
            link = str((item or {}).get("sp_link", "") or "")
            return (item.get("asset_name", ""), link) if item and link.startswith("http") else None

        excl = []
        for tok, step in zip(_COLLATERAL_TOKENS, _COLLATERAL_STEPS):
            item = content_audit.match_content_for_collateral(
                step_description=step, industry=industry, intent_topic=topic, exclude_ids=excl)
            pair = _link(item)
            if pair:
                hyperlink_slots[tok] = pair
                if item.get("id"):
                    excl.append(item["id"])

        for persona, contacts in slide_contacts.items():
            if not any(not getattr(c, "is_sentinel", False) for c in contacts):
                continue
            item = content_audit.match_content_for_supporting_asset(
                persona=persona, industry=industry, priority_area=topic)
            pair = _link(item)
            if pair:
                outreach_hyperlinks[persona] = {_SUPPORTING_ASSET_TOKEN: pair}
    except Exception as exc:  # noqa: BLE001
        logger.warning("v3.1 content-audit linking failed (continuing): %s", exc)
    return hyperlink_slots, outreach_hyperlinks


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
    # Ensure the seller name + pull date are available to the factual-token fill
    # (the legacy flow sets seller after this block; pull date isn't set at all).
    if not validated_data.get("salesperson_name"):
        validated_data["salesperson_name"] = company_data.get("salesperson_name", "")
    if not validated_data.get("pull_date"):
        import datetime
        validated_data["pull_date"] = datetime.date.today().strftime("%B %d, %Y")
    # Surface IT-budget estimate top-level for the factual token. The council emits
    # it under inconsistent keys (or omits it), so estimate_it_spend() checks every
    # variant then computes from employee count / revenue as a last resort.
    if not validated_data.get("estimated_it_spend"):
        validated_data["estimated_it_spend"] = estimate_it_spend(validated_data)

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

    # --- Stage 3: surgical contacts (validated, reliable).
    sel = await run_stage3(providers, canonical, canada_only=bool(company_data.get("canada_only")))

    # Final pass on ONLY the selected contacts: ZI Contact-Enrich (email/phone/
    # LinkedIn) + author per-contact bio/priorities/starters. Bounded to the ≤N
    # on the deck, so it's cheap, and it fills the slots that rendered blank.
    selected = [c for v in sel.slide_contacts.values() for c in v]
    try:
        await providers.enrich_final(selected, canonical.name)
    except Exception as e:  # noqa: BLE001 — enrichment is best-effort
        logger.warning("v3.1 enrich_final failed (continuing): %s", e)
    try:
        await formatter.author_contacts(selected, validated_data)
    except Exception as e:  # noqa: BLE001
        logger.warning("v3.1 author_contacts failed (continuing): %s", e)

    # Department: deterministic from the persona role when not provided by ZI.
    for c in selected:
        if getattr(c, "is_sentinel", False):
            continue
        if not (getattr(c, "department", "") or "").strip():
            c.department = DEPARTMENT_BY_PERSONA.get(c.persona, "")

    # Communication preference: derive from the contact methods we actually have.
    for c in selected:
        if getattr(c, "is_sentinel", False) or c.communication_preference:
            continue
        methods = [m for m, ok in (
            ("Phone", bool(c.phone or c.direct_phone or c.mobile_phone)),
            ("Email", bool(c.email)),
            ("LinkedIn", bool(c.linkedin_url)),
        ) if ok]
        c.communication_preference = " / ".join(methods)

    # Recompute the score now that contacts are enriched, then persist FIRST so a
    # render failure below still leaves the 6-bucket catalogue + score on the job.
    from bi_resolver import compute_data_quality_score
    sel.data_quality_score = compute_data_quality_score(sel.slide_contacts)
    validated_data["slide_contacts"] = _serialize(sel.slide_contacts)
    validated_data["contact_catalogue"] = _serialize(sel.contact_catalogue)
    validated_data["data_quality_score"] = sel.data_quality_score
    validated_data["enrichment_trace"] = sel.enrichment_trace
    logger.info("v3.1 contacts: %d across personas, dqs=%.2f",
                len(selected), sel.data_quality_score)

    # --- Stage 5/6: author + render the deck. If this raises, the caller catches
    # it, records the error, and falls back to the Gamma deck — but the contacts
    # above are already on the job (so the dashboard shows them either way).
    company_tokens = renderer.introspect_company_tokens()
    formatted = await formatter.build(validated_data, company_tokens, sel.slide_contacts)

    # Content-audit links: collateral (slide 9, by funnel step) + supporting asset
    # (per persona). Each becomes a hyperlinked asset name pointing at the DAM URL.
    hyperlink_slots, outreach_hyperlinks = _content_audit_links(validated_data, canonical, sel.slide_contacts)

    url = await renderer.render(
        slide_contacts=sel.slide_contacts,
        company_slots=formatted["company_slots"],
        outreach_slots=formatted["outreach_slots"],
        job_id=job_id,
        hyperlink_slots=hyperlink_slots,
        outreach_hyperlinks=outreach_hyperlinks,
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
