"""JobStore pure helpers + a full end-to-end pipeline_v31 run on fakes (no SDKs)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from bi_resolver import StakeholderRecord, CanonicalCompany, MIN_SLIDES  # noqa: E402
from job_store import (  # noqa: E402
    should_apply_update, build_progress_update, build_final_update, STAGE_SEQ,
)
from pipeline_v31 import run_pipeline_v31, _serialize_catalogue  # noqa: E402


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --- JobStore pure helpers ---------------------------------------------------

def test_monotonic_guard():
    assert should_apply_update(None, 1)
    assert should_apply_update(2, 3)
    assert should_apply_update(3, 3)
    assert not should_apply_update(5, 3)  # stale update dropped


def test_build_progress_update_shape():
    p = build_progress_update(stage="3_contacts", step="cascade", progress=1.5, partial={"x": 1})
    assert p["current_stage"] == "3_contacts"
    assert p["current_stage_seq"] == STAGE_SEQ["3_contacts"]
    assert p["step_progress"] == 1.0          # clamped
    assert p["status"] == "processing"
    assert p["_partial"] == {"x": 1}


def test_build_final_update_carries_artifacts():
    f = build_final_update({"slideshow_url": "u", "data_quality_score": 0.8,
                            "slide_contacts": {"CTO": []}, "warnings": ["w"]})
    assert f["status"] == "done" and f["slideshow_url"] == "u"
    assert f["data_quality_score"] == 0.8 and f["warnings"] == ["w"]


# --- end-to-end orchestration on fakes --------------------------------------

class FakeStore:
    def __init__(self):
        self.progress = []
        self.final = None
        self.failed = None
        self.logs = []

    def logger_sink(self, job_id):
        return lambda entries: self.logs.extend(entries)

    def update_progress(self, job_id, *, stage, step, progress, partial=None):
        self.progress.append(stage)

    def persist_final(self, job_id, result):
        self.final = result

    def fail(self, job_id, *, error_code, error_message):
        self.failed = (error_code, error_message)


def _complete(persona, name):
    return StakeholderRecord(persona=persona, name=name, title="Chief X Officer",
                             email=f"{name}@a.com", linkedin_url=f"https://li/{name}",
                             start_date="2024", source="zoominfo", tier=1, proximity=0)


class FakePipelineProviders:
    """Implements resolve_company/general_intel + the Stage-3 Providers seam."""
    def __init__(self):
        self.table = {
            ("CIO", "zoominfo", "csuite"): [_complete("CIO", "Ivy")],
            ("CTO", "zoominfo", "csuite"): [_complete("CTO", "Tom")],
            ("CFO", "zoominfo", "csuite"): [_complete("CFO", "Fay")],
            ("COO", "zoominfo", "csuite"): [_complete("COO", "Omar")],
        }

    async def resolve_company(self, company_data):
        return CanonicalCompany(name=company_data["company_name"], primary_domain="acme.com",
                                confidence=0.95)

    async def general_intel(self, canonical):
        return {"company_name": canonical.name, "signals": ["cloud"], "industry": "Tech"}

    async def query(self, persona, source, kind, canonical, canada_only):
        return list(self.table.get((persona, source, kind), []))

    async def judge_adjacency(self, title, persona):
        return True

    async def enrich(self, record):
        return record

    async def fallback(self, persona, canonical, canada_only):
        return None


class FakeFormatter:
    async def build(self, validated, slide_contacts):
        return {"company_slots": {"[Aviva Canada]": validated["company_name"]},
                "outreach_slots": {}}


class FakeRenderer:
    def __init__(self):
        self.called_with = None

    async def render(self, *, slide_contacts, company_slots, outreach_slots, job_id):
        self.called_with = (slide_contacts, company_slots)
        return f"https://supabase.example/decks/{job_id}.pptx"


async def _fake_council(general_intel, contact_payload):
    return dict(general_intel)  # echo facts (validation no-op for the wiring test)


def test_pipeline_v31_end_to_end():
    store = FakeStore()
    renderer = FakeRenderer()
    result = run(run_pipeline_v31(
        "job1", {"company_name": "Globex", "canada_only": False},
        store=store, providers=FakePipelineProviders(),
        council=_fake_council, formatter=FakeFormatter(), renderer=renderer,
    ))
    # all six stages + done were reported, in order
    assert store.progress[0] == "1_resolution" and store.progress[-1] == "done"
    for s in ("1_resolution", "2_general", "3_contacts", "4_council", "5_format", "6_render", "done"):
        assert s in store.progress
    # finalized with a deck URL + a real quality score
    assert store.final["slideshow_url"].endswith("job1.pptx")
    assert store.final["data_quality_score"] > 0
    assert store.failed is None
    # at least the floor of contacts, serialized to plain dicts
    flat = [c for v in store.final["slide_contacts"].values() for c in v]
    assert len(flat) >= MIN_SLIDES and isinstance(flat[0], dict)
    # logger flushed entries to the store sink
    assert store.logs and any(e["stage"] == "3_contacts" for e in store.logs)


def test_pipeline_v31_records_failure_on_store_row():
    class BoomProviders(FakePipelineProviders):
        async def resolve_company(self, company_data):
            raise ValueError("resolution exploded")

    store = FakeStore()
    try:
        run(run_pipeline_v31("job2", {"company_name": "X"}, store=store,
                             providers=BoomProviders(), council=_fake_council,
                             formatter=FakeFormatter(), renderer=FakeRenderer()))
    except ValueError:
        pass
    assert store.failed is not None and store.failed[0] == "ValueError"


def test_serialize_catalogue_plain_dicts():
    cat = {"CTO": [_complete("CTO", "Tom")], "CIO": []}
    out = _serialize_catalogue(cat)
    assert out["CTO"][0]["name"] == "Tom" and out["CIO"] == []
    assert isinstance(out["CTO"][0], dict)
