"""Post-restart job-status recovery + stale-job reaper (pure, stdlib-only).

The backend keeps live jobs in an in-memory dict (`jobs_store`) that Render wipes
on every restart/redeploy. Two failure modes follow from that:

  1. A job that completed before the restart is gone from memory, so a status poll
     404s and the portal shows it stuck "in progress". The durable `job_results`
     row is the recovery source — these helpers map it back to a status payload.
  2. A job whose worker dies mid-run is left "processing" forever (nothing flips it
     to failed). `is_stale_processing` lets a status poll reap it.

No FastAPI / Supabase imports here on purpose, so the decision logic is unit-tested
with stdlib only; production_main wires the Supabase I/O around it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

# How long an in-memory job may sit in "processing" before a status check reaps it
# to "failed". Generous: a full real run is minutes, not tens of minutes.
STALE_PROCESSING_MINUTES = 30


def resolve_persisted_status(row: dict) -> dict:
    """Map a durable `job_results` row (looked up when the job is NOT in memory) to a
    status payload for the portal.

    A row still marked 'processing' but absent from memory means the worker that
    owned it is gone (a restart wiped it): it will never finish, so we surface it as
    failed/interrupted rather than a perpetual 'processing' the UI spins on forever.
    """
    status = (row.get("status") or "").strip().lower()
    result = row.get("result")
    if status == "completed":
        return {"status": "completed", "progress": 100,
                "current_step": "Complete!", "result": result}
    if status == "failed":
        progress = result.get("progress", 0) if isinstance(result, dict) else 0
        return {"status": "failed", "progress": progress,
                "current_step": "Failed.", "result": result}
    # 'processing' (or unknown) found only in the durable store -> orphaned restart.
    return {
        "status": "failed",
        "progress": 0,
        "current_step": "Interrupted by a server restart before completing. Please re-run.",
        "result": result,
        "interrupted": True,
    }


def parse_iso(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp, tolerating a trailing 'Z' and naive (UTC-assumed)
    values. Returns a tz-aware datetime, or None if unparseable/empty."""
    if not ts:
        return None
    s = str(ts).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_stale_processing(status: str, created_at: str, now: datetime,
                        max_age_minutes: int = STALE_PROCESSING_MINUTES) -> bool:
    """True if an in-memory job has been 'processing' longer than the threshold — its
    worker hung or died without flipping the status. Such a job is reaped to 'failed'
    so the portal stops showing it as perpetually in progress."""
    if (status or "").strip().lower() != "processing":
        return False
    started = parse_iso(created_at)
    if started is None:
        return False
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age_minutes = (now - started).total_seconds() / 60.0
    return age_minutes >= max_age_minutes
