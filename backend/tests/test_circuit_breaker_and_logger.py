"""Unit tests for circuit_breaker.py and job_logger.py (stdlib-only)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from circuit_breaker import CircuitBreaker, CircuitBreakerRegistry  # noqa: E402
from job_logger import JobLogger, redact_email, redact_phone, redact_pii  # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


# --- circuit breaker ---------------------------------------------------------

def test_opens_after_threshold_failures():
    clk = FakeClock()
    cb = CircuitBreaker("zi", threshold=5, window_s=60, cooldown_s=30, clock=clk)
    for _ in range(4):
        cb.record_failure()
    assert not cb.is_open()
    cb.record_failure()  # 5th
    assert cb.is_open() and cb.state == "open"


def test_closes_after_cooldown():
    clk = FakeClock()
    cb = CircuitBreaker("zi", threshold=5, window_s=60, cooldown_s=30, clock=clk)
    for _ in range(5):
        cb.record_failure()
    assert cb.is_open()
    clk.t = 29
    assert cb.is_open()
    clk.t = 31  # cooldown elapsed -> half-open/closed
    assert not cb.is_open()


def test_success_resets_failures():
    cb = CircuitBreaker("zi", threshold=5)
    for _ in range(4):
        cb.record_failure()
    cb.record_success()
    for _ in range(4):
        cb.record_failure()
    assert not cb.is_open()  # 4 fresh failures, not 8


def test_failures_outside_window_dont_trip():
    clk = FakeClock()
    cb = CircuitBreaker("zi", threshold=5, window_s=60, clock=clk)
    for i in range(4):
        clk.t = i
        cb.record_failure()
    clk.t = 1000  # far outside window
    cb.record_failure()
    assert not cb.is_open()  # only 1 failure within the window


def test_registry_snapshot():
    reg = CircuitBreakerRegistry(threshold=2)
    reg.get("apollo").record_failure()
    reg.get("apollo").record_failure()
    reg.get("pdl")
    snap = reg.snapshot()
    assert snap["apollo"] == "open" and snap["pdl"] == "closed"


# --- PII redaction -----------------------------------------------------------

def test_redact_email():
    assert redact_email("ping john.doe@acme.com now") == "ping j***@acme.com now"


def test_redact_phone_keeps_last_four():
    out = redact_phone("call +1-555-867-5309 please")
    assert out.endswith("5309 please")
    assert "555" not in out and "867" not in out
    assert out.count("*") >= 6


def test_redact_phone_ignores_short_numbers():
    assert redact_phone("year 2024 and id 12345") == "year 2024 and id 12345"


def test_redact_recurses_dicts_and_lists():
    data = {"email": "a@b.com", "phones": ["+1 415 555 1212"], "n": 3}
    red = redact_pii(data)
    assert red["email"] == "a***@b.com"
    assert red["phones"][0].endswith("1212") and "415" not in red["phones"][0]
    assert red["n"] == 3


# --- JobLogger ---------------------------------------------------------------

def test_write_buffers_structured_entry_and_redacts():
    jl = JobLogger("job1", clock=lambda: 1.0)
    jl.info("3_contacts", "CFO cascade", "found alice@acme.com at +1-555-867-5309")
    e = jl.entries[0]
    assert e["stage"] == "3_contacts" and e["step"] == "CFO cascade" and e["level"] == "info"
    assert e["ts"] == 1.0
    assert "a***@acme.com" in e["msg"] and "867" not in e["msg"]


def test_redact_disabled_keeps_raw():
    jl = JobLogger("job1", redact=False)
    jl.info("s", "st", "email a@b.com")
    assert "a@b.com" in jl.entries[0]["msg"]


def test_flush_calls_sink_and_clears():
    seen = []
    jl = JobLogger("job1", sink=lambda entries: seen.append(list(entries)))
    jl.info("s", "st", "hello")
    jl.flush()
    assert len(seen) == 1 and len(seen[0]) == 1
    assert jl.entries == []  # cleared after successful flush


def test_flush_failure_does_not_raise_and_keeps_buffer():
    def bad_sink(_):
        raise RuntimeError("supabase down")

    jl = JobLogger("job1", sink=bad_sink)
    jl.info("s", "st", "hello")
    jl.flush()  # must not raise
    assert len(jl.entries) == 1  # retained for next flush


def test_context_manager_flushes_on_exception():
    seen = []
    try:
        with JobLogger("job1", sink=lambda e: seen.append(list(e))) as jl:
            jl.info("s", "st", "before boom")
            raise ValueError("boom")
    except ValueError:
        pass
    assert seen, "should have flushed on exit despite the exception"
    msgs = [e["msg"] for e in seen[0]]
    assert any("exception" in m for m in msgs)


def test_buffer_cap_drops_oldest():
    jl = JobLogger("job1", buffer_cap=10)
    for i in range(25):
        jl.info("s", "st", f"m{i}")
    assert len(jl.entries) == 10
    assert jl.entries[-1]["msg"] == "m24"  # newest kept
