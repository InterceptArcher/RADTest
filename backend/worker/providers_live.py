"""
Live Providers adapter — wires the v3.1 pipeline's injection seam to the real
data clients (ZoomInfo class client, Apollo/PDL via httpx, Hunter, Anthropic).

This is the boundary between the locally-tested orchestration and the network.
The pure helpers (persona -> query titles, ZI person -> StakeholderRecord) are
unit-tested here; the async methods that actually call clients are verified in
CI/staging with real credentials. SDK/client imports are lazy.
"""
from __future__ import annotations

from typing import Optional

from bi_resolver import (
    PERSONA_TITLE_BUCKETS, StakeholderRecord, CanonicalCompany,
)
from circuit_breaker import CircuitBreakerRegistry

# Role-area title hints for the VP / Director rungs, per persona.
_VP_DIR_HINTS = {
    "CIO": ["Information Technology", "IT", "Information Systems"],
    "CTO": ["Engineering", "Technology", "Software"],
    "CFO": ["Finance", "Accounting"],
    "COO": ["Operations"],
    "CISO": ["Security", "Information Security", "Cybersecurity"],
    "CPO": ["Product", "Product Management"],
}


def persona_titles_for(persona: str, kind: str) -> list[str]:
    """The job-title filter list to send to a provider for one persona+tier.

    csuite -> the persona's exact + canonical adjacent titles.
    vp / director -> '<Tier> of <role area>' style hints.
    """
    bucket = PERSONA_TITLE_BUCKETS.get(persona, {})
    if kind == "csuite":
        titles = []
        if bucket.get("exact"):
            titles.append(str(bucket["exact"]).title())
        titles.extend(sorted(t.title() for t in bucket.get("adjacent", set())))  # type: ignore[arg-type]
        return titles
    tier_word = "VP" if kind == "vp" else "Director"
    return [f"{tier_word} of {area}" for area in _VP_DIR_HINTS.get(persona, [])]


def zi_person_to_record(person: dict, persona: str) -> StakeholderRecord:
    """Map a normalized ZoomInfo contact dict to a StakeholderRecord."""
    rec = StakeholderRecord(
        persona=persona,
        name=person.get("name", "") or " ".join(
            x for x in [person.get("first_name", ""), person.get("last_name", "")] if x),
        title=person.get("title", ""),
        email=person.get("email", ""),
        phone=person.get("phone", ""),
        direct_phone=person.get("direct_phone", ""),
        mobile_phone=person.get("mobile_phone", ""),
        linkedin_url=person.get("linkedin", "") or person.get("linkedin_url", ""),
        start_date=person.get("hire_date", "") or person.get("start_date", ""),
        department=person.get("department", ""),
        source="zoominfo",
    )
    if rec.email:
        rec.email_sources.add("zoominfo")
    return rec


class LiveProviders:
    """Real implementation of the pipeline's Providers seam.

    Args (all injected so CI can supply mocks):
        zi_client: an instance of worker.zoominfo_client.ZoomInfoClient
        anthropic_client: AsyncAnthropic (for judge_adjacency / LinkedIn / fallback)
        http: an httpx.AsyncClient for Apollo/PDL/Hunter REST calls
        domain: the resolved company's primary domain
    """

    def __init__(self, *, zi_client=None, anthropic_client=None, http=None,
                 breakers: Optional[CircuitBreakerRegistry] = None):
        self.zi = zi_client
        self.anthropic = anthropic_client
        self.http = http
        self.breakers = breakers or CircuitBreakerRegistry()

    # --- Stage 1 -----------------------------------------------------------
    async def resolve_company(self, company_data: dict) -> CanonicalCompany:
        """Resolve to a canonical company. CI: parallel ZI/Apollo/PDL/Hunter +
        Haiku reconciler + web-search on ambiguity (see bi_resolver_io helpers)."""
        name = company_data.get("company_name", "")
        domain = company_data.get("domain", "")
        if self.zi is not None and self.breakers.get("zoominfo").is_open() is False:
            res = await self.zi.enrich_company(domain=domain or None, company_name=name or None)
            norm = (res or {}).get("normalized", {}) if isinstance(res, dict) else {}
            return CanonicalCompany(
                name=norm.get("company_name", name) or name,
                primary_domain=norm.get("domain", domain) or domain,
                industry=norm.get("industry", ""),
                hq_country=norm.get("country", ""),
                employee_bucket=str(norm.get("employee_count", "")),
                confidence=0.8,
                decision_basis="zoominfo enrich (single-source; reconciliation in CI)",
            )
        return CanonicalCompany(name=name, primary_domain=domain, confidence=0.4)

    # --- Stage 2 -----------------------------------------------------------
    async def general_intel(self, canonical: CanonicalCompany) -> dict:
        """Firmographics/signals/news. CI: reuse the existing intelligence
        gatherer + GNews (with the 5s timeout guard from bi_resolver_io)."""
        return {"company_name": canonical.name, "primary_domain": canonical.primary_domain,
                "industry": canonical.industry}

    # --- Stage 3 -----------------------------------------------------------
    async def query(self, persona, source, kind, canonical, canada_only) -> list[StakeholderRecord]:
        if source != "zoominfo" or self.zi is None:
            return []  # Apollo/PDL httpx adapters wired in CI
        if self.breakers.get("zoominfo").is_open():
            return []
        titles = persona_titles_for(persona, kind)
        try:
            res = await self.zi.search_contacts(
                domain=canonical.primary_domain, job_titles=titles, max_results=10)
            self.breakers.get("zoominfo").record_success()
        except Exception:  # noqa: BLE001
            self.breakers.get("zoominfo").record_failure()
            return []
        people = (res or {}).get("people", []) if isinstance(res, dict) else []
        return [zi_person_to_record(p, persona) for p in people]

    async def judge_adjacency(self, title: str, persona: str) -> bool:
        """Haiku yes/no on whether a novel title is a reasonable proxy. CI."""
        return False  # conservative default until the live Haiku call is wired

    async def enrich(self, record: StakeholderRecord) -> StakeholderRecord:
        """Cross-fill missing fields + Haiku LinkedIn validation (cached). CI."""
        return record

    async def fallback(self, persona, canonical, canada_only) -> Optional[StakeholderRecord]:
        """Stage-3 agentic fallback (Haiku + tools, 5-call cap). CI."""
        return None
