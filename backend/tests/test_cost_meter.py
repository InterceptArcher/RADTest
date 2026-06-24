"""Unit tests for worker.cost_meter — pure, no network, no pip deps.

Run directly with plain python3 (this devcontainer has no pytest):

    cd backend && python3 tests/test_cost_meter.py

CI runs these under pytest as well (each `test_*` function is collectable).
"""

import os
import sys

# Allow `import worker.cost_meter` whether invoked from backend/ or tests/.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
for p in (_BACKEND, os.path.join(_BACKEND, "worker")):
    if p not in sys.path:
        sys.path.insert(0, p)

import cost_meter  # noqa: E402  (imported from backend/worker via sys.path)


class _FakeUsage:
    """Mimics an Anthropic response.usage object (attribute access)."""

    def __init__(self, input_tokens, output_tokens, web_search_requests=None):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        if web_search_requests is not None:
            self.server_tool_use = _FakeServerToolUse(web_search_requests)


class _FakeServerToolUse:
    def __init__(self, web_search_requests):
        self.web_search_requests = web_search_requests


def test_pricing_substring_match():
    assert cost_meter._price_for_model("claude-haiku-4-5-20251001")["in"] == 1.0
    assert cost_meter._price_for_model("claude-sonnet-4-6")["out"] == 15.0
    assert cost_meter._price_for_model("claude-opus-4-1")["in"] == 15.0
    # Unknown id defaults to sonnet.
    assert cost_meter._price_for_model("mystery-model") == cost_meter.MODEL_PRICING["sonnet"]
    assert cost_meter._price_for_model("") == cost_meter.MODEL_PRICING["sonnet"]


def test_snapshot_math_and_shape():
    job = "job-test-1"
    cost_meter.reset(job)
    cost_meter.set_job(job)

    # Sonnet: 1,000,000 in @ $3 + 500,000 out @ $15 = 3.0 + 7.5 = 10.5 USD
    cost_meter.record_anthropic("claude-sonnet-4-6", _FakeUsage(1_000_000, 500_000))
    # Haiku: 200,000 in @ $1 + 100,000 out @ $5 = 0.2 + 0.5 = 0.7 USD
    cost_meter.record_anthropic("claude-haiku-4-5", _FakeUsage(200_000, 100_000))
    # 3 ZoomInfo calls @ $0.10 = 0.30 USD
    cost_meter.record_call("zoominfo", 3)
    # 2 web_search tool uses @ $0.01 = 0.02 USD
    cost_meter.record_web_search(2)

    snap = cost_meter.snapshot(job)

    assert snap["by_service"]["anthropic"]["calls"] == 2
    assert snap["by_service"]["anthropic"]["input_tokens"] == 1_200_000
    assert snap["by_service"]["anthropic"]["output_tokens"] == 600_000
    assert snap["by_service"]["anthropic"]["usd"] == 11.2  # 10.5 + 0.7
    assert snap["by_service"]["zoominfo"] == {"calls": 3, "usd": 0.3}
    assert snap["by_service"]["web_search"] == {"calls": 2, "usd": 0.02}
    assert snap["tokens"] == {"input": 1_200_000, "output": 600_000}
    # total = 11.2 + 0.3 + 0.02 = 11.52
    assert snap["total_usd"] == 11.52


def test_record_anthropic_with_server_tool_use_web_search():
    job = "job-test-2"
    cost_meter.reset(job)
    cost_meter.set_job(job)
    # Anthropic response that also reports 4 web_search requests via usage.
    cost_meter.record_anthropic(
        "claude-sonnet-4-6", _FakeUsage(0, 0, web_search_requests=4)
    )
    snap = cost_meter.snapshot(job)
    assert snap["by_service"]["web_search"]["calls"] == 4
    assert snap["by_service"]["web_search"]["usd"] == 0.04
    assert snap["total_usd"] == 0.04


def test_missing_usage_treated_as_zero():
    job = "job-test-3"
    cost_meter.reset(job)
    cost_meter.set_job(job)
    cost_meter.record_anthropic("claude-haiku-4-5", None)              # None usage
    cost_meter.record_anthropic("claude-haiku-4-5", {})               # empty dict
    cost_meter.record_anthropic("claude-haiku-4-5", {"input_tokens": "oops"})  # bad type
    snap = cost_meter.snapshot(job)
    assert snap["total_usd"] == 0.0
    assert snap["by_service"]["anthropic"]["calls"] == 3
    assert snap["by_service"]["anthropic"]["input_tokens"] == 0


def test_dict_usage_supported():
    job = "job-test-4"
    cost_meter.reset(job)
    cost_meter.set_job(job)
    # usage as a plain dict (e.g. resp.usage.model_dump()).
    cost_meter.record_anthropic(
        "claude-opus-4-1",
        {"input_tokens": 100_000, "output_tokens": 10_000},
    )
    snap = cost_meter.snapshot(job)
    # opus: 100k in @ $15 + 10k out @ $75 = 1.5 + 0.75 = 2.25
    assert snap["by_service"]["anthropic"]["usd"] == 2.25
    assert snap["total_usd"] == 2.25


def test_unknown_job_returns_zeroed_snapshot():
    snap = cost_meter.snapshot("never-bound-job")
    assert snap["total_usd"] == 0.0
    assert snap["by_service"]["anthropic"]["calls"] == 0
    assert snap["by_service"]["zoominfo"]["calls"] == 0
    assert snap["by_service"]["web_search"]["calls"] == 0


def _run_all():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    print("\nAll cost_meter tests passed")


if __name__ == "__main__":
    _run_all()
