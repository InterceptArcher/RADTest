"""
Per-upstream circuit breaker (v3.1).

In-memory, per-worker-process. Policy (from the design doc): 5 consecutive
failures within a 60s window opens the circuit for 30s; while open the source is
skipped and the cascade moves on, and the breaker state is surfaced in the
enrichment trace. The clock is injectable so the logic is unit-testable without
sleeping.
"""
from __future__ import annotations

import time
from typing import Callable


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        threshold: int = 5,
        window_s: float = 60.0,
        cooldown_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.name = name
        self.threshold = threshold
        self.window_s = window_s
        self.cooldown_s = cooldown_s
        self._clock = clock
        self._failures: list[float] = []
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if self._clock() - self._opened_at < self.cooldown_s:
            return True
        # Cooldown elapsed -> half-open: clear state and allow a trial call.
        self._opened_at = None
        self._failures = []
        return False

    def record_success(self) -> None:
        self._failures = []
        self._opened_at = None

    def record_failure(self) -> None:
        now = self._clock()
        # Drop failures outside the rolling window so transient blips don't trip it.
        self._failures = [t for t in self._failures if now - t <= self.window_s]
        self._failures.append(now)
        if len(self._failures) >= self.threshold:
            self._opened_at = now

    @property
    def state(self) -> str:
        return "open" if self.is_open() else "closed"


class CircuitBreakerRegistry:
    """One breaker per upstream name (ZI/Apollo/PDL/Hunter/GNews/Anthropic)."""

    def __init__(self, **breaker_kwargs):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._kwargs = breaker_kwargs

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, **self._kwargs)
        return self._breakers[name]

    def snapshot(self) -> dict[str, str]:
        """{name: state} — for writing into the enrichment trace."""
        return {name: b.state for name, b in self._breakers.items()}
