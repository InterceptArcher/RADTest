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
        self._company_id_cache: dict = {}  # domain -> ZoomInfo companyId (resolved once)

    async def _resolve_company_id(self, domain: str) -> str:
        """Resolve (and cache) a domain to its ZoomInfo companyId — used to anchor
        name-based contact enrich precisely at large multi-entity firms."""
        if not domain or self.zi is None:
            return ""
        if domain in self._company_id_cache:
            return self._company_id_cache[domain]
        cid = ""
        try:
            res = await self.zi.enrich_company(domain=domain)
            norm = (res or {}).get("normalized") or {}
            cid = str(norm.get("company_id") or "")
        except Exception:  # noqa: BLE001
            cid = ""
        self._company_id_cache[domain] = cid
        return cid

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
                domain=canonical.primary_domain, job_titles=titles, max_results=10,
                canada_only=canada_only)
            self.breakers.get("zoominfo").record_success()
        except Exception:  # noqa: BLE001
            self.breakers.get("zoominfo").record_failure()
            return []
        people = (res or {}).get("people", []) if isinstance(res, dict) else []
        records = [zi_person_to_record(p, persona) for p in people]
        if canada_only:
            # search_contacts now restricts the query to Canada (no global fallback),
            # so these records ARE Canada-scoped; mark them for the dashboard trace.
            for r in records:
                r.mark("canada_only_filtered")
        return records

    @staticmethod
    def _missing_contact_method(c) -> bool:
        """True if the contact lacks email OR any phone (i.e. not fully reachable)."""
        return not (c.email and (c.phone or c.direct_phone or c.mobile_phone))

    @staticmethod
    def _apply_enrich(c, p: dict) -> None:
        """Fill empty contact fields on record `c` from a ZI-normalized person `p`."""
        c.email = c.email or p.get("email", "")
        c.phone = c.phone or p.get("phone", "")
        c.direct_phone = c.direct_phone or p.get("direct_phone", "")
        c.mobile_phone = c.mobile_phone or p.get("mobile_phone", "")
        c.linkedin_url = c.linkedin_url or p.get("linkedin", "") or p.get("linkedin_url", "")
        c.start_date = c.start_date or p.get("hire_date", "") or p.get("start_date", "")
        c.department = c.department or p.get("department", "")
        c.person_id = c.person_id or str(p.get("person_id") or p.get("id") or "")
        if c.email:
            c.email_sources.add("zoominfo")

    async def enrich_final(self, contacts: list, company_name: str = "",
                           company_domain: str = "") -> None:
        """Fill the SELECTED contacts to completeness (email/phone/LinkedIn/start),
        mutating in place. Order: (1) ZoomInfo Contact-Enrich by person_id, then
        (2) ZoomInfo Contact-Enrich by NAME (anchored on the resolved companyId when
        available, else company name) for anyone still missing email/phone — this
        covers web-discovered execs that have no ZI person_id yet but ARE in
        ZoomInfo — then (3) a bounded web search for LinkedIn + start_date. The goal
        is that the RIGHT person ends up fully reachable."""
        real = [c for c in contacts if not c.is_sentinel]
        if not real:
            return
        company_id = await self._resolve_company_id(company_domain) if company_domain else ""

        # 1) ZoomInfo Contact-Enrich (email/phone) by person_id.
        ids = [c.person_id for c in real if getattr(c, "person_id", "")]
        if self.zi is not None and ids:
            try:
                res = await self.zi.enrich_contacts(ids)
                people = (res or {}).get("people", []) if isinstance(res, dict) else []
                by_id = {str(p.get("person_id") or p.get("id") or ""): p for p in people}
                for c in real:
                    p = by_id.get(c.person_id)
                    if p:
                        self._apply_enrich(c, p)
                        c.mark("zi_contact_enriched")
            except Exception:  # noqa: BLE001
                pass

        # 2) ZoomInfo Contact-Enrich by NAME for contacts still missing a contact
        #    method (web-found execs with no person_id, or person_id misses).
        need_name = [c for c in real if c.name and self._missing_contact_method(c)]
        if self.zi is not None and need_name:
            try:
                payload = [{**self._split_name(c.name), "company_name": company_name}
                           for c in need_name]
                res = await self.zi.enrich_contacts_by_name(payload, company_id=company_id or None)
                people = (res or {}).get("people", []) if isinstance(res, dict) else []
                by_name = {self._norm_name(p.get("name", "")): p for p in people if p.get("name")}
                for c in need_name:
                    p = by_name.get(self._norm_name(c.name))
                    if p:
                        self._apply_enrich(c, p)
                        c.mark("zi_name_enriched")
            except Exception:  # noqa: BLE001
                pass

        # 3) Web search for LinkedIn URL + start_date where still missing (citation required).
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

    async def enrich_one(self, contact, company_name: str = "", company_domain: str = "") -> None:
        """Enrich a SINGLE contact to completeness (delegates to enrich_final). Used
        by the hook's relevance-ranked fallback walk when the top pick can't be made
        reachable and we try the next-most-relevant candidate."""
        await self.enrich_final([contact], company_name, company_domain)

    @staticmethod
    def _split_name(full: str) -> dict:
        parts = (full or "").strip().split()
        if len(parts) >= 2:
            return {"first_name": parts[0], "last_name": parts[-1], "full_name": full}
        return {"full_name": full}

    @staticmethod
    def _norm_name(name: str) -> str:
        return " ".join((name or "").lower().split())

    async def judge_adjacency(self, title: str, persona: str) -> bool:
        # Strict, domain-scoped adjacency: a title is a proxy ONLY if it sits in the
        # persona's functional domain at a senior level. This rejects unrelated
        # senior titles (Communications, HR, Legal, Investigations, Brand, etc.)
        # that ZoomInfo's generic C-Level pool surfaces — they used to slip through
        # a loose "reasonable proxy" judgement and win a slide over the real exec.
        text = await self._haiku_text(
            system=(
                "You decide if a job title belongs to the SAME functional domain as a target "
                "C-suite persona. Domains are DISTINCT — do not conflate CIO and CTO:\n"
                "- CIO = internal/enterprise INFORMATION technology: IT, information systems, "
                "digital workplace, enterprise applications, data/analytics platforms.\n"
                "- CTO = PRODUCT/build technology: engineering, software development, R&D, "
                "architecture, the technology the company sells.\n"
                "- CISO = security / information security / cybersecurity.\n"
                "- CFO = finance / accounting / treasury / controller.\n"
                "- COO = operations / supply chain / general management.\n"
                "- CPO = product management / product strategy.\n"
                "Answer 'yes' ONLY if the title clearly sits in THIS persona's domain at a senior "
                "level (C-level, SVP, VP, Head, or Director). A CTO is NOT a proxy for CIO and vice "
                "versa. Titles in unrelated functions — communications, HR/people, legal, marketing, "
                "sales, brand, investigations, facilities, administration, or an executive/CEO office "
                "role — are NOT proxies. Answer strictly 'yes' or 'no'."),
            user=f"Persona: {persona}. Title: '{title}'. In {persona}'s functional domain at a senior level? yes or no.",
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
