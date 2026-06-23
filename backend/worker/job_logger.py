"""
JobLogger — centralized, PII-redacted, per-job structured logging (v3.1).

Every job (regardless of seller) gets one JobLogger threaded through all stages.
It buffers structured entries and flushes them to a sink (in production, the
`profile_requests.debug_logs` jsonb column; in tests, an injected callable).

Design rules honored here:
- PII (emails/phones) is redacted in `write()` before buffering, unless
  `redact_pii=False` (gated on DEBUG_RAW_LOGS in the caller).
- The buffer is capped to avoid runaway memory on stuck jobs.
- Telemetry must never block the job: a sink failure logs to stderr and continues.
- Flushes on stage boundaries and on context-manager exit, including on exception.
"""
from __future__ import annotations

import re
import sys
import time
from typing import Callable, Literal, Optional

Level = Literal["info", "warn", "error"]

_BUFFER_CAP = 5000

_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*(@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
# A phone-like run: optional +, then >=10 digits possibly separated by - . ( ) space
_PHONE_RE = re.compile(r"\+?\d[\d\-\.\s()]{8,}\d")


def redact_email(text: str) -> str:
    return _EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)


def redact_phone(text: str) -> str:
    def _mask(m: re.Match) -> str:
        raw = m.group(0)
        total = sum(ch.isdigit() for ch in raw)
        if total < 10:
            return raw  # not actually a phone number
        out, seen = [], 0
        for ch in raw:
            if ch.isdigit():
                seen += 1
                out.append(ch if seen > total - 4 else "*")  # keep only the last 4 digits
            else:
                out.append(ch)
        return "".join(out)

    return _PHONE_RE.sub(_mask, text)


def redact_pii(value):
    """Recursively redact emails/phones in strings, lists, and dict values."""
    if isinstance(value, str):
        return redact_phone(redact_email(value))
    if isinstance(value, list):
        return [redact_pii(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_pii(v) for k, v in value.items()}
    return value


class JobLogger:
    def __init__(
        self,
        job_id: str,
        *,
        sink: Optional[Callable[[list[dict]], None]] = None,
        redact: bool = True,
        clock: Callable[[], float] = time.time,
        buffer_cap: int = _BUFFER_CAP,
    ):
        self.job_id = job_id
        self._sink = sink
        self._redact = redact
        self._clock = clock
        self._cap = buffer_cap
        self._buffer: list[dict] = []
        self._truncated = False

    def write(self, *, stage: str, step: str, level: Level, msg: str, data: Optional[dict] = None) -> None:
        entry = {
            "ts": self._clock(),
            "stage": stage,
            "step": step,
            "level": level,
            "msg": msg,
            "data": data or {},
        }
        if self._redact:
            entry["msg"] = redact_pii(entry["msg"])
            entry["data"] = redact_pii(entry["data"])
        self._buffer.append(entry)
        if len(self._buffer) > self._cap:
            self._buffer.pop(0)  # keep most-recent; drop oldest
            if not self._truncated:
                self._truncated = True

    # Convenience helpers
    def info(self, stage: str, step: str, msg: str, data: Optional[dict] = None) -> None:
        self.write(stage=stage, step=step, level="info", msg=msg, data=data)

    def warn(self, stage: str, step: str, msg: str, data: Optional[dict] = None) -> None:
        self.write(stage=stage, step=step, level="warn", msg=msg, data=data)

    def error(self, stage: str, step: str, msg: str, data: Optional[dict] = None) -> None:
        self.write(stage=stage, step=step, level="error", msg=msg, data=data)

    @property
    def entries(self) -> list[dict]:
        return list(self._buffer)

    def flush(self) -> None:
        if self._sink is None or not self._buffer:
            return
        try:
            self._sink(list(self._buffer))
            self._buffer = []  # only clear on a successful write
        except Exception as exc:  # telemetry must never block the job
            print(f"[JobLogger {self.job_id}] flush failed, continuing: {exc}", file=sys.stderr)

    def __enter__(self) -> "JobLogger":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self.write(stage="job", step="exit", level="error",
                       msg=f"job ended with exception: {exc_type.__name__}: {exc_val}")
        self.flush()
        return False  # never suppress exceptions
