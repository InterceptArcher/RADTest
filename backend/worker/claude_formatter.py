"""
Claude Formatter — Stage 5 (v3.1).

A single Sonnet 4.6 call authors slide-ready copy for the template's *authored*
tokens (overviews, signal descriptions, opportunity/pain-point blobs, sales-
program rationale, per-contact bios/priorities/starters, per-persona outreach).
Factual tokens (company name, account type, industry, IT-budget, seller, date)
come straight from validated facts and are NOT authored. All copy-shaping
concerns (tone, length, no-SKU, account bucketing) live here — the Council no
longer carries them.

`anthropic` is imported lazily; the prompt assembly, schema validation, outreach
greeting aggregation, and factual-token mapping are pure and unit-tested locally.
"""
from __future__ import annotations

import json
from typing import Optional

from pptx_renderer import join_first_names  # reuse the slash-joined greeting

FORMATTER_MODEL = "claude-sonnet-4-6"


class FormatterOutputInvalidError(RuntimeError):
    pass


class FormatterSlotMismatchError(RuntimeError):
    pass


# Factual company tokens (master example string -> validated-facts key). These
# are filled directly, never authored by the model.
FACTUAL_COMPANY_TOKENS = {
    "[Aviva Canada]": "company_name",
    "[Aviva Canada.]": "company_name",
    "[Private]": "company_type",
    "[Insurance – Property and Casualty]": "industry",
    "[$43.1M – $86.2M annually]": "estimated_it_spend",
    "[Evan Perkins]": "salesperson_name",
    "[May 21, 2026.]": "pull_date",
}


def is_factual_token(token: str) -> bool:
    return token in FACTUAL_COMPANY_TOKENS


def _resolve_fact(facts: dict, key: str) -> str:
    """Resolve a fact top-level, then from executive_snapshot (where the council
    nests several fields like estimated_it_spend)."""
    v = facts.get(key)
    if v:
        return str(v)
    es = facts.get("executive_snapshot") or {}
    v = es.get(key)
    return str(v) if v else ""


def build_factual_replacements(tokens: list[str], facts: dict) -> dict[str, str]:
    """Fill the factual company tokens present on a slide from validated facts."""
    out: dict[str, str] = {}
    for tok in tokens:
        key = FACTUAL_COMPANY_TOKENS.get(tok)
        if key is not None:
            out[tok] = _resolve_fact(facts, key)
    return out


def authored_tokens(tokens: list[str]) -> list[str]:
    """Tokens the model must author (everything that isn't a factual fill)."""
    return [t for t in tokens if not is_factual_token(t)]


def outreach_greeting(contacts: list) -> str:
    """Slash-joined first names for a persona's outreach slides ('Lisa/Marcus')."""
    return join_first_names([getattr(c, "name", "") for c in contacts
                             if not getattr(c, "is_sentinel", False)])


def council_contact_payload(slide_contacts: dict) -> list[dict]:
    """Stage-4 narrowing (Mitigation 10): hand the Council ONLY the selected
    slide contacts as minimal fact dicts — never the full catalogue."""
    payload = []
    for persona, contacts in slide_contacts.items():
        for c in contacts:
            if getattr(c, "is_sentinel", False):
                continue
            payload.append({
                "persona": persona,
                "name": getattr(c, "name", ""),
                "title": getattr(c, "title", ""),
                "email": getattr(c, "email", ""),
                "linkedin_url": getattr(c, "linkedin_url", ""),
                "start_date": getattr(c, "start_date", ""),
            })
    return payload


def validate_formatter_output(output: dict, required_tokens: set[str]) -> None:
    """Fail loud if the model omitted a required token or invented an unknown one."""
    if not isinstance(output, dict):
        raise FormatterOutputInvalidError("formatter output must be a JSON object")
    produced = set(output.keys())
    missing = required_tokens - produced
    if missing:
        raise FormatterOutputInvalidError(f"formatter omitted required slots: {sorted(missing)}")
    unknown = produced - required_tokens
    if unknown:
        raise FormatterSlotMismatchError(f"formatter produced unknown slots: {sorted(unknown)}")


SYSTEM_PROMPT = (
    "You are RAD's slide copywriter. Author concise, executive-ready copy for each "
    "requested slide token from the validated facts. Rules: no SKUs or product model "
    "numbers; bucket by account type; keep each value within typical slide length; "
    "for any 'Why:'/rationale token in the Recommended Sales Program, write a SINGLE "
    "tight clause of <=15 words (these sit in small boxes and must not overflow); "
    "for Key Signals titles/headlines (the bracketed heading above each signal), keep "
    "them to a concise phrase of <=6 words so the title does not wrap into the body; "
    "return STRICT JSON mapping each requested token string to its copy. Do not add, "
    "rename, or omit tokens."
)


def build_formatter_prompt(facts: dict, tokens_to_author: list[str]) -> tuple[str, str]:
    """Return (system, user). User carries the facts + the exact token list to fill."""
    user = (
        "VALIDATED FACTS:\n" + json.dumps(facts, ensure_ascii=False, indent=2) +
        "\n\nAUTHOR COPY FOR EXACTLY THESE TOKENS (return a JSON object whose keys are "
        "these exact strings):\n" + json.dumps(tokens_to_author, ensure_ascii=False, indent=2)
    )
    return SYSTEM_PROMPT, user


class ClaudeFormatter:
    """Single Sonnet 4.6 call with schema validation + retries (anthropic lazy)."""

    def __init__(self, api_key: Optional[str] = None, model: str = FORMATTER_MODEL):
        self._api_key = api_key
        self._model = model

    async def build(self, validated_facts: dict, company_tokens: list[str], slide_contacts: dict) -> dict:
        """Assemble everything the renderer needs for the single-instance slides
        and per-persona outreach.

        - company_slots: factual tokens filled from validated facts + authored
          prose tokens written by Sonnet (one call).
        - outreach_slots: per persona present, the slash-joined greeting (multi-
          contact personas → "Lisa/Marcus"). Body copy is persona-generic.
        """
        factual = build_factual_replacements(company_tokens, validated_facts)
        to_author = authored_tokens(company_tokens)
        authored = await self.author(validated_facts, to_author) if to_author else {}
        company_slots = {**factual, **authored}

        # Per-persona outreach token map (the Email/LinkedIn/Call slides are cloned
        # per persona by the renderer). Keyed by the master's example token strings.
        bs = validated_facts.get("buying_signals") or {}
        topics = bs.get("intent_topics") or [
            t.get("topic") for t in (bs.get("intent_topics_detailed") or []) if t.get("topic")]
        topic = str((topics[0] if topics else "") or "")
        company = str(validated_facts.get("company_name", "") or "")
        industry = str(validated_facts.get("industry", "") or "")
        seller = str(validated_facts.get("salesperson_name", "") or "")
        outreach_slots: dict[str, dict] = {}
        for persona, contacts in slide_contacts.items():
            real = [c for c in contacts if not getattr(c, "is_sentinel", False)]
            if not real:
                continue
            firsts = outreach_greeting(real)
            outreach_slots[persona] = {
                "[CTO]": persona,
                "[Aviva Canada]": company,
                "[Aviva Canada.]": company,
                "[Aviva Canada on Cloud Migration]": (f"{company} on {topic}" if topic else company),
                "[Lisa]": firsts,
                "[Lisa,]": (firsts + "," if firsts else ""),
                "[Cloud Migration]": topic,
                "[Cloud migration]": topic,
                "[Insurance]": industry,
                "[Insurance teams]": (f"{industry} teams" if industry else ""),
                "[Evan Perkins]": seller,
                "[phone number]": "",
                "[Maximize productivity with AI workstation laptops]": "",  # resource = fast-follow
            }
        return {"company_slots": company_slots, "outreach_slots": outreach_slots}

    async def author_contacts(self, contacts: list, facts: dict) -> None:
        """Author per-contact slide narrative (about / strategic_priorities /
        conversation_starters) in ONE Sonnet call, mutating the records in place.
        Without this the contact slides render with blank bio/priorities sections."""
        targets = [c for c in contacts if not getattr(c, "is_sentinel", False)]
        if not targets:
            return
        import os
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self._api_key or os.getenv("ANTHROPIC_API_KEY"))
        roster = [{"index": i, "name": c.name, "title": c.title, "persona": c.persona}
                  for i, c in enumerate(targets)]
        system = (
            "You write executive-ready stakeholder briefing copy for a sales deck. For each "
            "contact return JSON with: 'about' (2-3 sentence bio); 'strategic_priorities' — a "
            "list of EXACTLY 3 points, each formatted as 'Short Title – one concise clause' and "
            "kept tight (~12-20 words total per point; descriptive but not strung out), tied to "
            "their role and the company's situation; and 'conversation_starters' — a list of 2 "
            "open-ended QUESTIONS that ask about their role, mandate, and strategic priorities "
            "(NOT sales pitches, NOT product claims; genuine discovery questions a rep would ask). "
            "No fabricated facts beyond role-typical inference. "
            "Example priority: 'IT Strategy & Continuity – Maintaining momentum on key technology "
            "initiatives and ensuring stability across IT operations during the interim period.' "
            "Return STRICT JSON: a list of "
            '{"index": int, "about": str, "strategic_priorities": [str], "conversation_starters": [str]}.')
        user = ("COMPANY:\n" + json.dumps({k: facts.get(k) for k in ("company_name", "industry", "company_overview")}, ensure_ascii=False)
                + "\n\nCONTACTS:\n" + json.dumps(roster, ensure_ascii=False))
        try:
            resp = await client.messages.create(model=self._model, max_tokens=2048, temperature=0.3,
                                                 system=system, messages=[{"role": "user", "content": user}])
            text = "".join(getattr(b, "text", "") for b in resp.content)
            s = text[text.find("["):text.rfind("]") + 1]
            authored = json.loads(s)
        except Exception:  # noqa: BLE001 — narrative is best-effort; never block the deck
            return
        by_idx = {a.get("index"): a for a in authored if isinstance(a, dict)}
        for i, c in enumerate(targets):
            a = by_idx.get(i)
            if not a:
                continue
            c.about = c.about or str(a.get("about", ""))
            sp = a.get("strategic_priorities") or []
            if sp and not c.strategic_priorities:
                c.strategic_priorities = [str(x) for x in sp]
            if not c.conversation_starters:
                cs = a.get("conversation_starters")
                if isinstance(cs, list):
                    # point form — one question per line
                    c.conversation_starters = "\n".join(str(x) for x in cs)
                else:
                    c.conversation_starters = str(cs or "")

    async def author(self, facts: dict, tokens_to_author: list[str], *, max_retries: int = 3) -> dict:
        import os
        from anthropic import AsyncAnthropic  # lazy: not an import-time dependency

        client = AsyncAnthropic(api_key=self._api_key or os.getenv("ANTHROPIC_API_KEY"))
        system, user = build_formatter_prompt(facts, tokens_to_author)
        required = set(tokens_to_author)
        last_err: Optional[Exception] = None
        for _ in range(max_retries):
            resp = await client.messages.create(
                model=self._model, max_tokens=4096, temperature=0.2,
                system=system, messages=[{"role": "user", "content": user}],
            )
            text = "".join(getattr(b, "text", "") for b in resp.content)
            try:
                output = json.loads(_extract_json(text))
                validate_formatter_output(output, required)
                return output
            except (json.JSONDecodeError, FormatterOutputInvalidError, FormatterSlotMismatchError) as exc:
                last_err = exc
                user = user + f"\n\nYour previous output was invalid: {exc}. Return valid JSON with exactly the requested keys."
        raise FormatterOutputInvalidError(f"formatter failed after {max_retries} retries: {last_err}")


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of a model response (handles code fences)."""
    s = text.strip()
    if "```" in s:
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    return s[start:end + 1] if start != -1 and end != -1 else s
