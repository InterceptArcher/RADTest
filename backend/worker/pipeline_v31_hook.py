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


def deck_basename(company_name: str, date_iso: str, canada_only: bool = False) -> str:
    """Storage-key basename for the deck: hprad_<company-slug>_<YYYY-MM-DD>[_ca].

    The slug lowercases the company and keeps [a-z0-9], collapsing every other run
    of characters to a single underscore (so "AT&T, Inc." -> "at_t_inc"). A blank
    company falls back to 'company' so the key is always well-formed. A Canada-only
    run gets a "_ca" suffix so it never overwrites the company's global deck."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", (company_name or "").lower()).strip("_")
    return f"hprad_{slug or 'company'}_{date_iso}" + ("_ca" if canada_only else "")


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


def _has_phone(c) -> bool:
    return bool(getattr(c, "phone", "") or getattr(c, "direct_phone", "")
                or getattr(c, "mobile_phone", ""))


def _field_count(c) -> int:
    """How many of the three reachability fields {email, phone, linkedin} are present."""
    return int(bool(getattr(c, "email", ""))) + int(_has_phone(c)) + int(bool(getattr(c, "linkedin_url", "")))


def _meets_baseline(c) -> bool:
    """Display baseline — the minimum to put a contact on the deck: at least TWO of
    {email, phone, LinkedIn}. A rep needs a real way to reach the person; one field
    alone is too thin to ship (replaced/dropped if a better option exists), but the
    old email-AND-LinkedIn rule was too strict — it dropped execs with phone+email
    just because ZoomInfo had no LinkedIn URL. The hard floor (Pass B) can still pad
    below-baseline contacts back in as a last resort to guarantee the slide count."""
    return _field_count(c) >= 2


def _reachability_score(c) -> int:
    """Preference weight for ranking contactability: email(4) > phone(2) > LinkedIn(1).
    Encodes the desired order among 2-field contacts — phone+email(6) > email+LinkedIn(5)
    > phone+LinkedIn(3) — with all three = 7. Higher is more reachable."""
    return (4 if getattr(c, "email", "") else 0) + (2 if _has_phone(c) else 0) \
        + (1 if getattr(c, "linkedin_url", "") else 0)


def _is_reachable(c) -> bool:
    """Fully reachable = the complete contact suite (all three fields). Preferred when
    choosing replacements/backfills; not required to ship (baseline is >=2 fields)."""
    return _field_count(c) == 3


def _identity_keys(c) -> set:
    out = set()
    for v in (getattr(c, "linkedin_url", ""), getattr(c, "email", ""), getattr(c, "name", "")):
        if v and str(v).strip():
            out.add(str(v).strip().lower())
    return out


async def _enforce_contact_quality(sel, providers, company_name: str, company_domain: str = "",
                                   *, floor: int = 4, max_try: int = 4) -> None:
    """Two passes that make the deck's contacts both relevant AND usable.

    Pass A (baseline gate, replace-leaning): a contact must meet the display baseline
    (email + LinkedIn) to ship. Keep picks that meet it. For a persona whose pick is
    below baseline — including a relevant exec ZoomInfo can't reach — REPLACE it with
    the most-relevant catalogue contact that meets baseline (preferring fully
    reachable); if none can be enriched to baseline, DROP the persona (an unreachable
    name is not shown).

    Pass B (floor): ensure >= `floor` baseline-meeting contacts on the deck, deduped;
    if short, backfill from any persona's catalogue with baseline-meeting (preferring
    reachable) contacts, most-relevant first.
    """
    from bi_resolver import PERSONAS, rank_by_proximity

    if not hasattr(providers, "enrich_one"):
        return

    async def best_baseline_alt(persona, used: set):
        """Most-relevant catalogue contact for `persona` that can reach baseline."""
        chosen_ids = {id(c) for c in sel.slide_contacts.get(persona, [])}
        alts = [c for c in sel.contact_catalogue.get(persona, [])
                if not getattr(c, "is_sentinel", False) and id(c) not in chosen_ids
                and not (_identity_keys(c) & used)]
        best = None
        for cand in rank_by_proximity(alts)[:max_try]:
            await providers.enrich_one(cand, company_name, company_domain)
            if _is_reachable(cand):
                return cand  # fully reachable — take immediately
            if best is None and _meets_baseline(cand):
                best = cand  # remember first baseline-only, keep looking for reachable
        return best

    # Pass A — baseline gate / replacement.
    used: set = set()
    for persona in PERSONAS:
        picks = [c for c in sel.slide_contacts.get(persona, []) if not getattr(c, "is_sentinel", False)]
        kept = [c for c in picks if _meets_baseline(c)]
        if kept:
            sel.slide_contacts[persona] = kept
            for c in kept:
                used |= _identity_keys(c)
            continue
        repl = await best_baseline_alt(persona, used) if picks else None
        if repl is not None:
            repl.mark("replaced_below_baseline_pick")
            sel.slide_contacts[persona] = [repl]
            used |= _identity_keys(repl)
        else:
            sel.slide_contacts[persona] = []  # drop: no contactable person for this persona

    # Pass B — floor (an ABSOLUTE guarantee of `floor` contacts on the deck).
    def _deduped_count(predicate) -> int:
        seen: set = set()
        n = 0
        for v in sel.slide_contacts.values():
            for c in v:
                if getattr(c, "is_sentinel", False) or not predicate(c):
                    continue
                ks = _identity_keys(c)
                if ks & seen:
                    continue
                seen |= ks
                n += 1
        return n

    def baseline_count() -> int:
        return _deduped_count(_meets_baseline)

    def contact_count() -> int:
        return _deduped_count(lambda c: True)

    def free_pool() -> list:
        pool = []
        for persona in PERSONAS:
            chosen_ids = {id(c) for c in sel.slide_contacts.get(persona, [])}
            for c in sel.contact_catalogue.get(persona, []):
                if getattr(c, "is_sentinel", False) or id(c) in chosen_ids or (_identity_keys(c) & used):
                    continue
                pool.append(c)
        return pool

    # B1 — prefer to reach the floor with baseline-meeting (>=2 field) contacts,
    # most-relevant first; enrich each candidate before judging reachability.
    if baseline_count() < floor:
        for cand in rank_by_proximity(free_pool()):
            if baseline_count() >= floor:
                break
            await providers.enrich_one(cand, company_name, company_domain)
            if _meets_baseline(cand) and not (_identity_keys(cand) & used):
                cand.mark("reachability_floor_addition")
                sel.slide_contacts.setdefault(cand.persona, []).append(cand)
                used |= _identity_keys(cand)

    # B2 — HARD floor. If still short of `floor` real contacts, pad with the
    # best-available below-baseline contacts (most fields first, then reachability,
    # then relevance): a thin contact beats an empty slot. This NEVER fabricates —
    # it only uses catalogue contacts we actually gathered, so a company that truly
    # yielded fewer than `floor` candidates still ships fewer (we don't invent
    # people). Geo top-up (Stage 3) widens that pool for non-Canada-HQ companies.
    if contact_count() < floor:
        leftovers = sorted(
            free_pool(),
            key=lambda c: (-_field_count(c), -_reachability_score(c), c.proximity, c.tier, c.name),
        )
        for cand in leftovers:
            if contact_count() >= floor:
                break
            if _identity_keys(cand) & used:
                continue
            cand.mark("hard_floor_below_baseline_pad")
            sel.slide_contacts.setdefault(cand.persona, []).append(cand)
            used |= _identity_keys(cand)


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
    # Re-bind the cost meter to this job so v3.1 Anthropic/ZoomInfo/web-search
    # calls are attributed even if the contextvar didn't propagate. Best-effort.
    try:
        import cost_meter
        cost_meter.set_job(job_id)
    except Exception:  # noqa: BLE001
        pass

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
        # Free-text HQ location ("City, Province/State, Country"); the only country
        # signal we have. Drives the geo top-up decision for canada_only runs:
        # non-Canada-HQ companies may top up to the floor with NA/global contacts,
        # genuinely Canadian ones stay strict. See bi_resolver_io._is_canada_hq.
        hq_country=(validated_data.get("hq_country") or validated_data.get("headquarters")
                    or company_data.get("headquarters", "")),
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
    # LinkedIn by id, then by name) + bounded web search. Bounded to the ≤N on the
    # deck, so it's cheap, and it fills the slots that rendered blank.
    selected = [c for v in sel.slide_contacts.values() for c in v]
    try:
        await providers.enrich_final(selected, canonical.name, canonical.primary_domain)
    except Exception as e:  # noqa: BLE001 — enrichment is best-effort
        logger.warning("v3.1 enrich_final failed (continuing): %s", e)

    # Contact-quality gate + reachability floor. A contact must meet a display
    # baseline (email + LinkedIn) to ship — a name a rep can't reach is worse than
    # nothing. Below-baseline picks (incl. relevant execs ZoomInfo can't reach) are
    # REPLACED by the most-relevant catalogue contact that meets baseline, or dropped
    # if none. Then we backfill to >= 4 baseline-meeting contacts on the deck.
    try:
        await _enforce_contact_quality(sel, providers, canonical.name, canonical.primary_domain, floor=4)
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.warning("v3.1 enforce_contact_quality failed (continuing): %s", e)
    selected = [c for v in sel.slide_contacts.values() for c in v]

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

    # Deck filename: hprad_<company>_<date> (human-readable in Storage / on the
    # downloaded file) instead of the opaque internal job id.
    import datetime
    deck_name = deck_basename(canonical.name, datetime.date.today().isoformat(),
                              canada_only=bool(company_data.get("canada_only")))

    url = await renderer.render(
        slide_contacts=sel.slide_contacts,
        company_slots=formatted["company_slots"],
        outreach_slots=formatted["outreach_slots"],
        job_id=job_id,
        hyperlink_slots=hyperlink_slots,
        outreach_hyperlinks=outreach_hyperlinks,
        deck_name=deck_name,
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
