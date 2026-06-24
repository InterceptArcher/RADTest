"""Per-job API cost instrumentation (ADDITIVE, best-effort, no behavior change).

This module meters the estimated USD cost of external API calls made while
processing a single job. It is intentionally:

  * **Pure / dependency-free at import time** — no anthropic, httpx, supabase
    or any other heavy import at module top, so it is safe to import anywhere
    (and unit-testable with plain `python3`, no pytest/pip required).
  * **Best-effort** — every recording entry point swallows its own errors. A
    failure to meter must NEVER propagate into the pipeline. Cost metering is
    observational only; the pipeline behaves identically whether metering
    succeeds or not.

Usage (call sites):

    from worker import cost_meter            # or `import cost_meter`
    cost_meter.set_job(job_id)               # bind once at start of processing
    ...
    cost_meter.record_anthropic(model, resp.usage)   # after messages.create()
    cost_meter.record_call("zoominfo")               # per ZoomInfo API call
    ...
    snap = cost_meter.snapshot(job_id)       # -> dict for the frontend meter

The job id is bound to a ``contextvars.ContextVar`` so call sites that already
run inside the job's task don't need the id threaded through their signatures.
"""

from __future__ import annotations

import contextvars
import threading
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# PRICING CONSTANTS  (edit here)
# ---------------------------------------------------------------------------
# Anthropic model pricing in USD **per 1,000,000 tokens**, split by input /
# output. Matched against the model id by substring (see `_price_for_model`).
# These are rough public list-price estimates and are intended to be easy to
# tweak in one place.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "haiku":  {"in": 1.0,  "out": 5.0},
    "sonnet": {"in": 3.0,  "out": 15.0},
    "opus":   {"in": 15.0, "out": 75.0},
}
# Default pricing when a model id matches none of the substrings above.
_DEFAULT_MODEL_KEY = "sonnet"

# OpenAI model pricing (USD per 1,000,000 tokens) — the 28-specialist LLM Council
# runs on OpenAI (gpt-4o-mini by default). Matched by substring; default = mini.
OPENAI_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o":      {"in": 2.50, "out": 10.0},
    "gpt-4":       {"in": 30.0, "out": 60.0},
    "gpt-3.5":     {"in": 0.50, "out": 1.50},
}
_DEFAULT_OPENAI_KEY = "gpt-4o-mini"

# Flat per-use prices in USD.
WEB_SEARCH_USD_PER_CALL = 0.01   # one Anthropic web_search tool invocation
ZOOMINFO_USD_PER_CALL = 0.10     # one ZoomInfo GTM API call (rough credit est.)

# Round the reported total to this many decimal places.
_USD_ROUND = 4


# ---------------------------------------------------------------------------
# Registry + contextvar
# ---------------------------------------------------------------------------
current_job_id: "contextvars.ContextVar[Optional[str]]" = contextvars.ContextVar(
    "current_job_id", default=None
)

# job_id -> CostAccumulator. Guarded by a lock for the rare cross-thread case.
_REGISTRY: "Dict[str, CostAccumulator]" = {}
_LOCK = threading.Lock()


class CostAccumulator:
    """Mutable per-job tally. All numbers are additive; never decremented."""

    def __init__(self) -> None:
        # Anthropic
        self.anthropic_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.anthropic_usd = 0.0
        # OpenAI (LLM Council)
        self.openai_calls = 0
        self.openai_input_tokens = 0
        self.openai_output_tokens = 0
        self.openai_usd = 0.0
        # ZoomInfo
        self.zoominfo_calls = 0
        self.zoominfo_usd = 0.0
        # Web search (Anthropic server-side tool)
        self.web_search_calls = 0
        self.web_search_usd = 0.0

    # -- recording ----------------------------------------------------------
    def add_anthropic(self, model: str, in_tok: int, out_tok: int) -> None:
        price = _price_for_model(model)
        self.anthropic_calls += 1
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.anthropic_usd += (
            in_tok * price["in"] + out_tok * price["out"]
        ) / 1_000_000.0

    def add_openai(self, model: str, in_tok: int, out_tok: int) -> None:
        price = _price_for_openai(model)
        self.openai_calls += 1
        self.openai_input_tokens += in_tok
        self.openai_output_tokens += out_tok
        self.openai_usd += (
            in_tok * price["in"] + out_tok * price["out"]
        ) / 1_000_000.0

    def add_web_search(self, n: int) -> None:
        if n <= 0:
            return
        self.web_search_calls += n
        self.web_search_usd += n * WEB_SEARCH_USD_PER_CALL

    def add_zoominfo(self, n: int) -> None:
        if n <= 0:
            return
        self.zoominfo_calls += n
        self.zoominfo_usd += n * ZOOMINFO_USD_PER_CALL

    # -- reporting ----------------------------------------------------------
    def to_snapshot(self) -> Dict[str, Any]:
        total = (self.anthropic_usd + self.openai_usd
                 + self.zoominfo_usd + self.web_search_usd)
        return {
            "total_usd": round(total, _USD_ROUND),
            "by_service": {
                "anthropic": {
                    "calls": self.anthropic_calls,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens,
                    "usd": round(self.anthropic_usd, _USD_ROUND),
                },
                "openai": {
                    "calls": self.openai_calls,
                    "input_tokens": self.openai_input_tokens,
                    "output_tokens": self.openai_output_tokens,
                    "usd": round(self.openai_usd, _USD_ROUND),
                },
                "zoominfo": {
                    "calls": self.zoominfo_calls,
                    "usd": round(self.zoominfo_usd, _USD_ROUND),
                },
                "web_search": {
                    "calls": self.web_search_calls,
                    "usd": round(self.web_search_usd, _USD_ROUND),
                },
            },
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
        }


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def _price_for_model(model: str) -> Dict[str, float]:
    """Return the per-1M-token price dict for `model`, matched by substring.

    Order is checked explicitly; defaults to sonnet pricing for unknown ids.
    """
    m = (model or "").lower()
    for key in ("haiku", "sonnet", "opus"):
        if key in m:
            return MODEL_PRICING[key]
    return MODEL_PRICING[_DEFAULT_MODEL_KEY]


def _price_for_openai(model: str) -> Dict[str, float]:
    """Per-1M-token price for an OpenAI model id (longest match first)."""
    m = (model or "").lower()
    for key in ("gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5"):
        if key in m:
            return OPENAI_PRICING[key]
    return OPENAI_PRICING[_DEFAULT_OPENAI_KEY]


def _int(val: Any) -> int:
    """Coerce a possibly-missing usage field to a non-negative int (0 on miss)."""
    try:
        if val is None:
            return 0
        return max(0, int(val))
    except (TypeError, ValueError):
        return 0


def _usage_field(usage: Any, name: str) -> Any:
    """Read `name` from a usage object whether it's an attr or a dict key."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(name)
    return getattr(usage, name, None)


def _web_search_requests(usage: Any) -> int:
    """Pull `server_tool_use.web_search_requests` from a usage object if present."""
    stu = _usage_field(usage, "server_tool_use")
    if stu is None:
        return 0
    return _int(_usage_field(stu, "web_search_requests"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def set_job(job_id: str) -> None:
    """Bind `job_id` to the contextvar and ensure an accumulator exists.

    Safe to call more than once for the same job (the existing accumulator is
    preserved so re-binding inside a sub-pipeline keeps the running tally).
    """
    current_job_id.set(job_id)
    with _LOCK:
        if job_id not in _REGISTRY:
            _REGISTRY[job_id] = CostAccumulator()


def _get(job_id: Optional[str]) -> Optional[CostAccumulator]:
    if job_id is None:
        job_id = current_job_id.get()
    if job_id is None:
        return None
    with _LOCK:
        return _REGISTRY.get(job_id)


def record_anthropic(model: str, usage: Any, *, job_id: Optional[str] = None) -> None:
    """Record one Anthropic `messages.create` response's token cost.

    `usage` is the response's `.usage` (object or dict). Robust to missing
    fields (treated as 0). Also adds web-search cost when the usage exposes
    `server_tool_use.web_search_requests`.
    """
    acc = _get(job_id)
    if acc is None:
        return
    acc.add_anthropic(
        model,
        _int(_usage_field(usage, "input_tokens")),
        _int(_usage_field(usage, "output_tokens")),
    )
    acc.add_web_search(_web_search_requests(usage))


def record_openai(model: str, usage: Any, *, job_id: Optional[str] = None) -> None:
    """Record one OpenAI chat-completion response's token cost (the LLM Council).

    `usage` is the response's `.usage` (object or dict) with `prompt_tokens` /
    `completion_tokens`. Robust to missing fields (treated as 0).
    """
    acc = _get(job_id)
    if acc is None:
        return
    acc.add_openai(
        model,
        _int(_usage_field(usage, "prompt_tokens")),
        _int(_usage_field(usage, "completion_tokens")),
    )


def record_call(service: str, n: int = 1, *, job_id: Optional[str] = None) -> None:
    """Record `n` flat-rate calls for `service` (currently `zoominfo`)."""
    acc = _get(job_id)
    if acc is None:
        return
    if service == "zoominfo":
        acc.add_zoominfo(n)
    elif service == "web_search":
        acc.add_web_search(n)
    # Unknown services are ignored (best-effort; never raise).


def record_web_search(n: int = 1, *, job_id: Optional[str] = None) -> None:
    """Record `n` Anthropic web_search tool invocations explicitly."""
    acc = _get(job_id)
    if acc is None:
        return
    acc.add_web_search(n)


def snapshot(job_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the cost snapshot dict for `job_id` (or the bound contextvar).

    Always returns a well-formed (zeroed) snapshot even if the job is unknown,
    so callers can persist it unconditionally.
    """
    acc = _get(job_id)
    if acc is None:
        return CostAccumulator().to_snapshot()
    return acc.to_snapshot()


def reset(job_id: str) -> None:
    """Drop the accumulator for `job_id` (optional cleanup; not required)."""
    with _LOCK:
        _REGISTRY.pop(job_id, None)
