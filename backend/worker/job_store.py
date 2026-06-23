"""
JobStore — Supabase persistence for the central `profile_requests` table (v3.1).

Replaces the in-memory `jobs_store` dict: every job is created, progressed, and
finalized here, so devops can pull any job's state + debug log straight from the
database. Provides the JobLogger flush sink (appends redacted entries to
`profile_requests.debug_logs`).

The supabase client is imported lazily; the payload-building and monotonic-guard
logic is pure and unit-tested locally.
"""
from __future__ import annotations

from typing import Callable, Optional

STAGE_SEQ = {  # canonical stage -> monotonic sequence for the out-of-order guard
    "1_resolution": 1,
    "2_general": 2,
    "3_contacts": 3,
    "4_council": 4,
    "5_format": 5,
    "6_render": 6,
    "done": 7,
    "failed": 7,
}


def should_apply_update(current_seq: Optional[int], new_seq: int) -> bool:
    """Monotonic guard: only advance progress forward (Mitigation: out-of-order writes)."""
    return current_seq is None or new_seq >= current_seq


def build_progress_update(*, stage: str, step: str, progress: float,
                          partial: Optional[dict] = None) -> dict:
    """Shape the row update for a stage transition."""
    payload = {
        "current_stage": stage,
        "current_step": step,
        "current_stage_seq": STAGE_SEQ.get(stage, 0),
        "step_progress": round(max(0.0, min(1.0, progress)), 2),
        "status": "done" if stage == "done" else ("failed" if stage == "failed" else "processing"),
    }
    if partial:
        payload["_partial"] = partial  # merged into partial_results by the writer
    return payload


def build_final_update(result: dict) -> dict:
    """Shape the row update when the pipeline completes."""
    return {
        "status": "done",
        "current_stage": "done",
        "current_stage_seq": STAGE_SEQ["done"],
        "step_progress": 1.0,
        "slideshow_url": result.get("slideshow_url"),
        "slide_contacts": result.get("slide_contacts", {}),
        "contact_catalogue": result.get("contact_catalogue", {}),
        "enrichment_trace": result.get("enrichment_trace", []),
        "data_quality_score": result.get("data_quality_score"),
        "warnings": result.get("warnings", []),
    }


class JobStore:
    """Thin Supabase wrapper around `profile_requests` (supabase imported lazily)."""

    TABLE = "profile_requests"

    def __init__(self, client=None):
        self._client = client  # inject in tests; lazily created in prod via factory

    @classmethod
    def from_env(cls) -> "JobStore":
        import os
        from supabase import create_client  # lazy
        return cls(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]))

    def create_job(self, *, input_name: str, salesperson_name: str = "", canada_only: bool = False) -> str:
        row = {"input_name": input_name, "salesperson_name": salesperson_name,
               "canada_only": canada_only, "status": "queued"}
        res = self._client.table(self.TABLE).insert(row).execute()
        return res.data[0]["id"]

    def update_progress(self, job_id: str, *, stage: str, step: str,
                        progress: float, partial: Optional[dict] = None) -> None:
        new_seq = STAGE_SEQ.get(stage, 0)
        current = self._client.table(self.TABLE).select("current_stage_seq,partial_results") \
            .eq("id", job_id).single().execute().data
        if not should_apply_update(current.get("current_stage_seq"), new_seq):
            return  # stale/out-of-order update — drop it
        payload = build_progress_update(stage=stage, step=step, progress=progress, partial=partial)
        merged_partial = dict(current.get("partial_results") or {})
        if "_partial" in payload:
            merged_partial.update(payload.pop("_partial"))
            payload["partial_results"] = merged_partial
        payload["updated_at"] = "now()"
        self._client.table(self.TABLE).update(payload).eq("id", job_id).execute()

    def persist_final(self, job_id: str, result: dict) -> None:
        self._client.table(self.TABLE).update(build_final_update(result)).eq("id", job_id).execute()

    def fail(self, job_id: str, *, error_code: str, error_message: str) -> None:
        self._client.table(self.TABLE).update({
            "status": "failed", "current_stage": "failed",
            "error_code": error_code, "error_message": error_message,
        }).eq("id", job_id).execute()

    def logger_sink(self, job_id: str) -> Callable[[list[dict]], None]:
        """Return a JobLogger sink that appends entries to debug_logs."""
        def _sink(entries: list[dict]) -> None:
            current = self._client.table(self.TABLE).select("debug_logs") \
                .eq("id", job_id).single().execute().data
            logs = list(current.get("debug_logs") or [])
            logs.extend(entries)
            self._client.table(self.TABLE).update({"debug_logs": logs}).eq("id", job_id).execute()
        return _sink
