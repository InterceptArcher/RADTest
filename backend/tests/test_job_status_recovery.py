"""Unit tests for the post-restart job-status recovery + stale-reaper helpers.

Pure stdlib (no FastAPI/Supabase), so these run anywhere the worker package is
importable. They pin the behavior that fixes:
  - jobs perpetually showing "in progress" after a Render redeploy, and
  - jobs stuck "processing" forever when their worker dies mid-run.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from job_status_recovery import (  # noqa: E402
    resolve_persisted_status, is_stale_processing, parse_iso,
)


def test_completed_row_resolves_to_completed():
    out = resolve_persisted_status({"status": "completed", "result": {"x": 1}})
    assert out["status"] == "completed" and out["progress"] == 100
    assert out["result"] == {"x": 1}


def test_failed_row_resolves_to_failed():
    out = resolve_persisted_status({"status": "failed", "result": {"error": "boom"}})
    assert out["status"] == "failed"


def test_orphaned_processing_row_resolves_to_failed_interrupted():
    # A 'processing' row found ONLY in the durable store (not in memory) means the
    # worker was wiped by a restart -> surface failed/interrupted, not perpetual
    # 'processing'.
    out = resolve_persisted_status({"status": "processing", "result": None})
    assert out["status"] == "failed" and out.get("interrupted") is True
    assert "restart" in out["current_step"].lower()


def test_unknown_status_treated_as_interrupted():
    out = resolve_persisted_status({"status": "", "result": None})
    assert out["status"] == "failed" and out.get("interrupted") is True


def test_stale_processing_true_after_threshold():
    now = datetime(2026, 6, 24, 14, 0, 0, tzinfo=timezone.utc)
    started = (now - timedelta(minutes=45)).isoformat()
    assert is_stale_processing("processing", started, now, max_age_minutes=30)


def test_stale_processing_false_when_recent():
    now = datetime(2026, 6, 24, 14, 0, 0, tzinfo=timezone.utc)
    started = (now - timedelta(minutes=5)).isoformat()
    assert not is_stale_processing("processing", started, now, max_age_minutes=30)


def test_stale_processing_false_for_completed():
    now = datetime(2026, 6, 24, 14, 0, 0, tzinfo=timezone.utc)
    started = (now - timedelta(hours=5)).isoformat()
    assert not is_stale_processing("completed", started, now)


def test_stale_processing_false_when_no_timestamp():
    now = datetime(2026, 6, 24, 14, 0, 0, tzinfo=timezone.utc)
    assert not is_stale_processing("processing", "", now)


def test_parse_iso_handles_z_suffix_and_naive():
    assert parse_iso("2026-06-24T13:29:36.403Z") is not None
    assert parse_iso("2026-06-24T13:29:36.403") is not None
    assert parse_iso("") is None
    assert parse_iso("not-a-date") is None
