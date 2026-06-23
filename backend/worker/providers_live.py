"""
Live Providers adapter — wires the v3.1 pipeline's injection seam to the real
data clients. Built on the EXISTING, docs-validated ZoomInfo GTM API v1 client
(worker.zoominfo_client) plus Anthropic Haiku for adjacency judgement and
LinkedIn enrichment.

Validated 2026-06-23 against docs.zoominfo.com: the contact-search endpoint
(/gtm/data/v1/contacts/search), JSON:API body, jobTitle/managementLevel/
companyPastOrPresent filters, page[size] pagination, and application/vnd.api+json
content-type all match the current docs, so reusing the client is correct.

Pure helpers (persona->titles, ZI person->record) are unit-tested. The async
methods are mock-tested with fakes; live verification happens on a real prod job.
SDK/client imports are lazy.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from bi_resolver import PERSONA_TITLE_BUCKETS, StakeholderRecord, CanonicalCompany
from circuit_breaker import CircuitBreakerRegistry

HAIKU_MODEL = "claude-haiku-4-5-20251001"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}

_VP_DIR_HINTS = {
    "CIO": ["Information Technology", "IT", "Information Systems"],
    "CTO": ["Engineering", "Technology", "Software"],
    "CFO": ["Finance", "Accounting"],
    "COO": ["Operations"],
    "CISO": ["Security", "Information Security", "Cybersecurity"],
    "CPO": ["Product", "Product Management"],
}


def persona_titles_for(persona: str, kind: str) -> list[str]:
    """Job-title filter list for one persona+tier (csuite uses the canonical bucket)."""
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
        person_id=str(person.get("person_id", "") or person.get("id", "")),
    )
    if rec.email:
        rec.email_sources.add("zoominfo")
    return rec


def _extract_json(text: str) -> dict:
    s = (text or "").strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return {}


class LiveProviders:
    """Real Providers seam. zi_client + anthropic_client injected (CI uses mocks)."""

    def __init__(self, *, zi_client=None, anthropic_client=None,
                 breakers: Optional[CircuitBreakerRegistry] = None):
        self.zi = zi_client
        self._anthropic = anthropic_client
        self.breakers = breakers or CircuitBreakerRegistry()

    # --- Anthropic helpers -------------------------------------------------
    def _anthropic_or_none(self):
        if self._anthropic is not None:
            return self._anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        from anthropic import AsyncAnthropic  # lazy
        self._anthropic = AsyncAnthropic(api_key=key)
        return self._anthropic

    async def _haiku_text(self, system: str, user: str, *, tools=None, max_tokens=512) -> str:
        client = self._anthropic_or_none()
        if client is None:
            return ""
        kwargs = dict(model=HAIKU_MODEL, max_tokens=max_tokens, system=system,
                      messages=[{"role": "user", "content": user}])
        if tools:
            kwargs["tools"] = tools
        resp = await client.messages.create(**kwargs)
        return "".join(getattr(b, "text", "") for b in resp.content)

    # --- Stage 1 -----------------------------------------------------------
    async def resolve_company(self, company_data: dict) -> CanonicalCompany:
        name = company_data.get("company_name", "")
        domain = company_data.get("domain", "")
        if self.zi is not None and not self.breakers.get("zoominfo").is_open():
            try:
                res = await self.zi.enrich_company(domain=domain or None, company_name=name or None)
                self.breakers.get("zoominfo").record_success()
            except Exception:  # noqa: BLE001
                self.breakers.get("zoominfo").record_failure()
                res = None
            norm = (res or {}).get("normalized", {}) if isinstance(res, dict) else {}
            if norm:
                return CanonicalCompany(
                    name=norm.get("company_name", name) or name,
                    primary_domain=norm.get("domain", domain) or domain,
                    industry=norm.get("industry", ""),
                    hq_country=norm.get("country", ""),
                    employee_bucket=str(norm.get("employee_count", "")),
                    confidence=0.8,
                    decision_basis="zoominfo enrich (multi-source reconciliation = follow-up)",
                )
        return CanonicalCompany(name=name, primary_domain=domain, confidence=0.4,
                                decision_basis="fallback: input echoed (no ZI resolution)")

    # --- Stage 2 -----------------------------------------------------------
    async def general_intel(self, canonical: CanonicalCompany) -> dict:
        """Minimal firmographics surface. The flag-gated integration reuses the
        existing rich intel pipeline for this stage; this is the standalone path."""
        return {
            "company_name": canonical.name,
            "primary_domain": canonical.primary_domain,
            "industry": canonical.industry,
            "company_type": "",
            "estimated_it_spend": "",
        }

    # --- Stage 3 -----------------------------------------------------------
    async def query(self, persona, source, kind, canonical, canada_only) -> list[StakeholderRecord]:
        # Reuse the validated ZoomInfo client. Its search already cascades
        # C-suite->VP->Director internally and returns a priority-sorted pool, so
        # we issue ONE csuite-scoped call per persona and let bi_resolver grade
        # proximity. VP/Director/Apollo/PDL rungs are no-ops here (ZI covers them);
        # they remain available for a future multi-source expansion.
        if source != "zoominfo" or self.zi is None or kind != "csuite":
            return []
        if self.breakers.get("zoominfo").is_open():
            return []
        titles = persona_titles_for(persona, "csuite")
        try:
            res = await self.zi.search_contacts(
                domain=canonical.primary_domain, job_titles=titles, max_results=10)
            self.breakers.get("zoominfo").record_success()
        except Exception:  # noqa: BLE001
            self.breakers.get("zoominfo").record_failure()
            return []
        people = (res or {}).get("people", []) if isinstance(res, dict) else []
        records = [zi_person_to_record(p, persona) for p in people]
        if canada_only:
            # The existing client prefers North America but has no strict country
            # param; flag the limitation rather than silently returning global.
            for r in records:
                r.mark("canada_only_requested:zi_na_preference_only")
        return records

    async def enrich_final(self, contacts: list, company_name: str = "") -> None:
        """Final pass on the SELECTED contacts (≤N, cheap): ZoomInfo Contact-Enrich
        for email/phone, then a bounded web search to fill LinkedIn + start_date
        (which ZI enrich doesn't provide). Mutates records in place."""
        real = [c for c in contacts if not c.is_sentinel]

        # 1) ZoomInfo Contact-Enrich (email/phone) by person_id.
        ids = [c.person_id for c in real if getattr(c, "person_id", "")]
        if self.zi is not None and ids:
            try:
                res = await self.zi.enrich_contacts(ids)
                people = (res or {}).get("people", []) if isinstance(res, dict) else []
                by_id = {str(p.get("person_id") or p.get("id") or ""): p for p in people}
                for c in real:
                    p = by_id.get(c.person_id)
                    if not p:
                        continue
                    c.email = c.email or p.get("email", "")
                    c.phone = c.phone or p.get("phone", "")
                    c.direct_phone = c.direct_phone or p.get("direct_phone", "")
                    c.mobile_phone = c.mobile_phone or p.get("mobile_phone", "")
                    c.linkedin_url = c.linkedin_url or p.get("linkedin", "") or p.get("linkedin_url", "")
                    c.start_date = c.start_date or p.get("hire_date", "") or p.get("start_date", "")
                    c.department = c.department or p.get("department", "")
                    if c.email:
                        c.email_sources.add("zoominfo")
                    c.mark("zi_contact_enriched")
            except Exception:  # noqa: BLE001
                pass

        # 2) Web search for LinkedIn URL + start_date where still missing (citation required).
        if self._anthropic_or_none() is None:
            return
        for c in real:
            if c.linkedin_url and c.start_date:
                continue
            text = await self._haiku_text(
                system=("Find a person's LinkedIn profile URL and the date they started their "
                        "current role. Return STRICT JSON {\"linkedin_url\": str, \"start_date\": str, "
                        "\"extracted_snippet\": str, \"source_url\": str}. Only fill a field from a "
                        "source you actually read; otherwise use an empty string. Do not fabricate."),
                user=f"{c.name}, {c.title} at {company_name}. Find their LinkedIn URL and role start date.",
                tools=[WEB_SEARCH_TOOL], max_tokens=400,
            )
            data = _extract_json(text)
            if data.get("extracted_snippet"):
                c.linkedin_url = c.linkedin_url or str(data.get("linkedin_url") or "")
                c.start_date = c.start_date or str(data.get("start_date") or "")
                c.mark("web_enriched_linkedin_start")

    async def judge_adjacency(self, title: str, persona: str) -> bool:
        text = await self._haiku_text(
            system="You judge whether a job title is a reasonable proxy for a target executive persona. Answer strictly 'yes' or 'no'.",
            user=f"Is the title '{title}' a reasonable proxy for the {persona} of a company? Answer yes or no.",
            max_tokens=8,
        )
        return text.strip().lower().startswith("y")

    async def enrich(self, record: StakeholderRecord) -> StakeholderRecord:
        # Cross-fill from other sources = follow-up. Here we do the always-on
        # Haiku LinkedIn validation for start_date (Mitigation 3: require a
        # citation, else treat the field as missing — never fabricate).
        if record.start_date or not record.linkedin_url:
            return record
        if self._anthropic_or_none() is None:
            record.mark("linkedin_enrich:no_anthropic")
            return record
        text = await self._haiku_text(
            system="You extract a person's start date at their current company from their LinkedIn page. Return STRICT JSON: {\"start_date\": string|null, \"current_position_confirmed\": bool, \"extracted_snippet\": string, \"source_url\": string}. Only fill start_date if you can quote the snippet you read it from.",
            user=f"Find the start date for {record.name} at their current role. LinkedIn: {record.linkedin_url}",
            tools=[WEB_SEARCH_TOOL], max_tokens=400,
        )
        data = _extract_json(text)
        if data.get("start_date") and data.get("extracted_snippet"):
            record.start_date = str(data["start_date"])
            record.mark("linkedin_start_date_verified")
        else:
            record.mark("linkedin_enrich:no_citation_or_not_found")
        return record

    async def fallback(self, persona, canonical, canada_only) -> Optional[StakeholderRecord]:
        # Agentic last resort. Conservative: only return a contact if Haiku web
        # search confirms a name AND a source; otherwise None (floor-fill sentinels).
        if self._anthropic_or_none() is None:
            return None
        text = await self._haiku_text(
            system="You find ONE senior person closest to a target role at a company, confirmed by web search. Return STRICT JSON: {\"name\": string|null, \"title\": string, \"linkedin_url\": string, \"source_url\": string}. Return name=null if you cannot confirm with a real source. Do NOT fabricate.",
            user=f"Find the {persona} (or closest senior equivalent) at {canonical.name} ({canonical.primary_domain}).",
            tools=[WEB_SEARCH_TOOL], max_tokens=400,
        )
        data = _extract_json(text)
        if not data.get("name") or not data.get("source_url"):
            return None
        rec = StakeholderRecord(persona=persona, name=str(data["name"]),
                                title=str(data.get("title", "")),
                                linkedin_url=str(data.get("linkedin_url", "")),
                                source="agent")
        rec.mark("fallback_agent_found:" + str(data.get("source_url", ""))[:60])
        return rec
