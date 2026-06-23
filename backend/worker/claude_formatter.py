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


def build_factual_replacements(tokens: list[str], facts: dict) -> dict[str, str]:
    """Fill the factual company tokens present on a slide from validated facts."""
    out: dict[str, str] = {}
    for tok in tokens:
        key = FACTUAL_COMPANY_TOKENS.get(tok)
        if key is not None:
            out[tok] = str(facts.get(key, "") or "")
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
