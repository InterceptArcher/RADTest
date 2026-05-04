"""
TDD tests for Gamma pending-recovery (Fix A: extended polling ceiling, Fix B:
async reconciliation of generations that outlast the polling window).

Background — see backend/production_main.py:2517 → worker/gamma_slideshow.py.
The original polling loop in _send_to_gamma raised on timeout and discarded
the generation_id, so a slideshow that Gamma eventually finished was lost
to the system entirely. These tests describe the desired new behavior:

  1. _send_to_gamma extends its polling ceiling from 150 → 300 attempts (600 s).
  2. On timeout, _send_to_gamma RETURNS a pending result with the generation_id
     instead of raising.
  3. create_slideshow propagates slideshow_status='pending' and slideshow_id.
  4. A new check_generation_status method does a single non-polling check.
  5. A new reconcile_pending_generation method polls until terminal.
  6. /job-status performs an inline lazy reconcile when slideshow is pending.

Tests use a fake httpx.AsyncClient (not the real network) and mock asyncio.sleep
so the full polling ceiling runs in milliseconds.
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

import httpx
import pytest


# ---------------------------------------------------------------------------
# Fake httpx machinery
# ---------------------------------------------------------------------------

class FakeResponse:
    """Stand-in for httpx.Response."""

    def __init__(self, status_code: int = 200, json_data: Optional[dict] = None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = str(json_data) if json_data else ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            req = httpx.Request("GET", "http://fake")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=req, response=self
            )

    def json(self) -> dict:
        return self._json


class FakeAsyncClient:
    """
    Stand-in for httpx.AsyncClient that returns pre-scripted responses.

    Receives a shared `counter` dict so the GET attempt index advances even
    across multiple AsyncClient instantiations — required for testing
    reconcile_pending_generation, which opens a fresh client per poll.
    """

    def __init__(
        self,
        post_response: FakeResponse,
        get_response_fn: Callable[[int], FakeResponse],
        counter: Dict[str, int],
        *args,
        **kwargs,
    ):
        self._post_response = post_response
        self._get_response_fn = get_response_fn
        self._counter = counter

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def post(self, *args, **kwargs) -> FakeResponse:
        return self._post_response

    async def get(self, *args, **kwargs) -> FakeResponse:
        self._counter["n"] += 1
        return self._get_response_fn(self._counter["n"])


def _make_async_client_factory(
    post_response: FakeResponse,
    get_response_fn: Callable[[int], FakeResponse],
):
    """Returns a callable suitable for monkeypatching httpx.AsyncClient."""
    counter = {"n": 0}

    def _factory(*args, **kwargs):
        return FakeAsyncClient(post_response, get_response_fn, counter, *args, **kwargs)
    return _factory


# ---------------------------------------------------------------------------
# Fix A — extended polling ceiling (150 → 300 attempts, 600 seconds)
# ---------------------------------------------------------------------------

async def test_send_to_gamma_polls_up_to_300_attempts():
    """
    The polling ceiling MUST be raised from 150 → 300 attempts so Gamma's
    slower template-based generations (which can sit in queue >5 min) succeed.

    We assert via the public attribute polling_max_attempts so the value can
    also be overridden per-instance for tests.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    assert getattr(creator, "polling_max_attempts", None) == 300, (
        "polling_max_attempts must default to 300 (600 s @ 2 s/attempt) — "
        "Fix A from BC Liquor 2026-05-03 incident."
    )


async def test_send_to_gamma_succeeds_when_gamma_completes_within_window():
    """
    Mock Gamma to return 'pending' for 250 polls then 'completed' with a URL.
    Old ceiling (150) would have timed out; new ceiling (300) succeeds.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    post_resp = FakeResponse(201, {"generationId": "gen-late-bloomer"})

    def get_fn(attempt: int) -> FakeResponse:
        if attempt < 251:
            return FakeResponse(200, {"status": "pending"})
        return FakeResponse(200, {
            "status": "completed",
            "gammaUrl": "https://gamma.app/docs/late-bloomer",
        })

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)), \
         patch("worker.gamma_slideshow.asyncio.sleep", new=_no_op_sleep):
        result = await creator._send_to_gamma(
            markdown_content="# test",
            num_cards=10,
            company_data={"company_name": "Test", "validated_data": {}},
        )

    assert result["url"] == "https://gamma.app/docs/late-bloomer"
    assert result["id"] == "gen-late-bloomer"


# ---------------------------------------------------------------------------
# Fix B core — pending result on timeout (no raise, generation_id preserved)
# ---------------------------------------------------------------------------

async def test_send_to_gamma_returns_pending_on_timeout_instead_of_raising():
    """
    When polling exhausts max_attempts without reaching a terminal state,
    _send_to_gamma MUST return {status:'pending', id:<gen_id>, url:None}
    instead of raising. The generation_id is the only handle the system has
    for later reconciliation, so it MUST NOT be discarded.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    creator.polling_max_attempts = 3   # keep the test fast

    post_resp = FakeResponse(201, {"generationId": "gen-stuck-pending"})

    def get_fn(attempt: int) -> FakeResponse:
        return FakeResponse(200, {"status": "pending"})

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)), \
         patch("worker.gamma_slideshow.asyncio.sleep", new=_no_op_sleep):
        result = await creator._send_to_gamma(
            markdown_content="# test",
            num_cards=10,
            company_data={"company_name": "Test", "validated_data": {}},
        )

    assert result.get("status") == "pending", (
        f"timeout MUST return status=pending (got {result.get('status')!r}) — "
        "raising and discarding the generation_id is the original BC Liquor bug"
    )
    assert result.get("id") == "gen-stuck-pending"
    assert result.get("url") is None


# ---------------------------------------------------------------------------
# create_slideshow propagates pending status (so the pipeline can spawn the
# background reconcile and the frontend can keep polling)
# ---------------------------------------------------------------------------

async def test_create_slideshow_propagates_pending_status_and_generation_id():
    """
    When _send_to_gamma reports pending, create_slideshow's outer envelope
    MUST surface slideshow_status='pending' and slideshow_id=<gen_id>.
    success stays True because nothing has actually failed — generation
    is in flight and reconciliation will land the URL later.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    async def fake_send(*args, **kwargs):
        return {"url": None, "id": "gen-still-cooking", "status": "pending"}

    with patch.object(creator, "_send_to_gamma", new=fake_send):
        result = await creator.create_slideshow({
            "company_name": "Test Co",
            "validated_data": {"company_name": "Test Co"},
            "confidence_score": 0.85,
        })

    assert result["success"] is True, "pending is not a failure"
    assert result["slideshow_status"] == "pending"
    assert result["slideshow_id"] == "gen-still-cooking"
    assert result["slideshow_url"] is None


async def test_create_slideshow_propagates_completed_status_for_finished_runs():
    """Backwards compat: completed runs still report slideshow_status='completed'."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    async def fake_send(*args, **kwargs):
        return {
            "url": "https://gamma.app/docs/abc",
            "id": "gen-done",
            "status": "generated",
        }

    with patch.object(creator, "_send_to_gamma", new=fake_send):
        result = await creator.create_slideshow({
            "company_name": "Test Co",
            "validated_data": {"company_name": "Test Co"},
            "confidence_score": 0.85,
        })

    assert result["success"] is True
    assert result["slideshow_status"] == "completed"
    assert result["slideshow_url"] == "https://gamma.app/docs/abc"
    assert result["slideshow_id"] == "gen-done"


# ---------------------------------------------------------------------------
# check_generation_status — single non-polling status fetch
# ---------------------------------------------------------------------------

async def test_check_generation_status_returns_completed_with_url():
    """
    A new lightweight method check_generation_status(generation_id) MUST
    perform exactly ONE Gamma status GET (no polling) and return a
    structured dict suitable for both the lazy /job-status reconcile and
    the background reconcile loop.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    post_resp = FakeResponse(200, {})  # not used, only GET happens

    def get_fn(attempt: int) -> FakeResponse:
        return FakeResponse(200, {
            "status": "completed",
            "gammaUrl": "https://gamma.app/docs/now-done",
        })

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)):
        result = await creator.check_generation_status("gen-x")

    assert result["status"] == "completed"
    assert result["url"] == "https://gamma.app/docs/now-done"
    assert result["error"] is None


async def test_check_generation_status_returns_pending_when_still_pending():
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    post_resp = FakeResponse(200, {})

    def get_fn(attempt: int) -> FakeResponse:
        return FakeResponse(200, {"status": "pending"})

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)):
        result = await creator.check_generation_status("gen-x")

    assert result["status"] == "pending"
    assert result["url"] is None


# ---------------------------------------------------------------------------
# reconcile_pending_generation — loops until terminal or hard cap
# ---------------------------------------------------------------------------

async def test_reconcile_pending_generation_returns_url_when_done():
    """
    The background reconcile loop polls Gamma until it returns a terminal
    status, then returns the URL. It uses a longer hard cap (default 30 min)
    than _send_to_gamma's per-request poll, since it runs out of band.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    post_resp = FakeResponse(200, {})

    def get_fn(attempt: int) -> FakeResponse:
        if attempt < 4:
            return FakeResponse(200, {"status": "pending"})
        return FakeResponse(200, {
            "status": "completed",
            "gammaUrl": "https://gamma.app/docs/reconciled",
        })

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)), \
         patch("worker.gamma_slideshow.asyncio.sleep", new=_no_op_sleep):
        result = await creator.reconcile_pending_generation(
            "gen-reconcile",
            max_total_seconds=60,
            poll_interval_seconds=2,
        )

    assert result["status"] == "completed"
    assert result["url"] == "https://gamma.app/docs/reconciled"


async def test_reconcile_pending_generation_gives_up_at_hard_cap():
    """If Gamma never finishes, reconcile gives up at max_total_seconds."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")

    post_resp = FakeResponse(200, {})

    def get_fn(attempt: int) -> FakeResponse:
        return FakeResponse(200, {"status": "pending"})

    with patch("worker.gamma_slideshow.httpx.AsyncClient",
               new=_make_async_client_factory(post_resp, get_fn)), \
         patch("worker.gamma_slideshow.asyncio.sleep", new=_no_op_sleep):
        result = await creator.reconcile_pending_generation(
            "gen-eternal-pending",
            max_total_seconds=4,
            poll_interval_seconds=2,
        )

    # At hard cap, status reports the last-seen value (pending), with url=None
    assert result["status"] in ("pending", "timeout")
    assert result["url"] is None


# ---------------------------------------------------------------------------
# /job-status endpoint — inline lazy reconcile
# ---------------------------------------------------------------------------

async def test_job_status_endpoint_lazy_reconciles_pending_slideshow():
    """
    When a job's stored result has slideshow_status='pending' and
    slideshow_id is set, /job-status MUST perform an inline single-shot
    Gamma status check before returning. If Gamma now reports completed,
    the job's result is updated in place.
    """
    import production_main as pm
    from fastapi.testclient import TestClient

    job_id = "test-pending-job-001"
    pm.jobs_store[job_id] = {
        "status": "completed",
        "progress": 100,
        "current_step": "Complete!",
        "created_at": "2026-05-03T00:00:00Z",
        "result": {
            "success": True,
            "company_name": "Test Co",
            "slideshow_url": None,
            "slideshow_id": "gen-pending-xyz",
            "slideshow_status": "pending",
        },
        "slideshow_data": {
            "success": True,
            "slideshow_url": None,
            "slideshow_id": "gen-pending-xyz",
            "slideshow_status": "pending",
        },
    }

    # Mock the Gamma status check used by the lazy reconcile so it reports
    # the slideshow is now finished.
    async def fake_check(self, generation_id):
        return {
            "status": "completed",
            "url": "https://gamma.app/docs/lazily-reconciled",
            "id": generation_id,
            "error": None,
        }

    with patch("worker.gamma_slideshow.GammaSlideshowCreator.check_generation_status",
               new=fake_check), \
         patch.object(pm, "GAMMA_API_KEY", "test-key"):
        client = TestClient(pm.app)
        resp = client.get(f"/job-status/{job_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["slideshow_url"] == "https://gamma.app/docs/lazily-reconciled"
    assert body["result"]["slideshow_status"] == "completed"

    # Mutation MUST persist in jobs_store so subsequent polls return cached value
    assert pm.jobs_store[job_id]["result"]["slideshow_url"] == "https://gamma.app/docs/lazily-reconciled"
    assert pm.jobs_store[job_id]["result"]["slideshow_status"] == "completed"

    # Cleanup
    del pm.jobs_store[job_id]


async def test_job_status_endpoint_does_not_reconcile_when_slideshow_already_completed():
    """Lazy reconcile MUST be a no-op for jobs whose slideshow is already done."""
    import production_main as pm
    from fastapi.testclient import TestClient

    job_id = "test-already-done-002"
    pm.jobs_store[job_id] = {
        "status": "completed",
        "progress": 100,
        "current_step": "Complete!",
        "created_at": "2026-05-03T00:00:00Z",
        "result": {
            "success": True,
            "company_name": "Test Co",
            "slideshow_url": "https://gamma.app/docs/already-here",
            "slideshow_id": "gen-old",
            "slideshow_status": "completed",
        },
    }

    call_count = {"n": 0}

    async def fake_check(self, generation_id):
        call_count["n"] += 1
        return {"status": "completed", "url": "should-not-be-used", "id": generation_id, "error": None}

    with patch("worker.gamma_slideshow.GammaSlideshowCreator.check_generation_status",
               new=fake_check), \
         patch.object(pm, "GAMMA_API_KEY", "test-key"):
        client = TestClient(pm.app)
        resp = client.get(f"/job-status/{job_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["slideshow_url"] == "https://gamma.app/docs/already-here"
    assert call_count["n"] == 0, "lazy reconcile must not call Gamma when slideshow is already completed"

    del pm.jobs_store[job_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _no_op_sleep(*args, **kwargs):
    """Replacement for asyncio.sleep that returns immediately."""
    return None
