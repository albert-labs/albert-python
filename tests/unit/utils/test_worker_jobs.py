"""Tests for poll_worker_job: termination on success/failure states and timeout."""

import time
from typing import Any

import pytest

from albert.exceptions import AlbertException
from albert.resources.worker_jobs import WorkerJobState
from albert.utils.worker_jobs import poll_worker_job


class _JsonResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def json(self) -> dict[str, Any]:
        return self._data


class _FakeSession:
    """Returns a scripted sequence of worker-job bodies, one per GET call."""

    def __init__(self, bodies: list[dict[str, Any]]) -> None:
        self._bodies = list(bodies)
        self.calls = 0

    def get(self, path: str) -> _JsonResponse:
        self.calls += 1
        return _JsonResponse(self._bodies.pop(0))


def _job_body(state: str, *, state_message: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"jobType": "importCSV", "metadata": {}, "state": state}
    if state_message is not None:
        body["stateMessage"] = state_message
    return body


def test_poll_worker_job_returns_immediately_on_success():
    """Test that a job already successful on the first poll returns without retrying."""
    session = _FakeSession([_job_body("successful")])

    job = poll_worker_job(session=session, job_id="JOB1", poll_interval=0.01, max_wait=0.01)

    assert job.state == WorkerJobState.SUCCESSFUL
    assert session.calls == 1


def test_poll_worker_job_retries_through_pending_states(monkeypatch: pytest.MonkeyPatch):
    """Test that inProgress/submitted states are retried until a terminal state is reached."""
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    session = _FakeSession(
        [
            _job_body("submitted"),
            _job_body("inProgress"),
            _job_body("successful"),
        ]
    )

    job = poll_worker_job(session=session, job_id="JOB1", poll_interval=0.01, max_wait=0.01)

    assert job.state == WorkerJobState.SUCCESSFUL
    assert session.calls == 3
    assert len(sleeps) == 2


def test_poll_worker_job_raises_on_failure_with_state_message():
    """Test that a failed job raises AlbertException carrying the job's state_message."""
    session = _FakeSession([_job_body("failed", state_message="disk full")])

    with pytest.raises(AlbertException, match="disk full"):
        poll_worker_job(session=session, job_id="JOB1", poll_interval=0.01, max_wait=0.01)


def test_poll_worker_job_failure_message_falls_back_without_state_message():
    """Test that a failed job with no state_message reports the raw state instead."""
    session = _FakeSession([_job_body("failed")])

    with pytest.raises(AlbertException, match="job state is failed"):
        poll_worker_job(session=session, job_id="JOB1", poll_interval=0.01, max_wait=0.01)


def test_poll_worker_job_raises_on_cancelled():
    """Test that a cancelled job also raises AlbertException by default."""
    session = _FakeSession([_job_body("cancelled")])

    with pytest.raises(AlbertException, match="job state is cancelled"):
        poll_worker_job(session=session, job_id="JOB1", poll_interval=0.01, max_wait=0.01)


def test_poll_worker_job_returns_failed_job_when_raise_on_failure_false():
    """Test that raise_on_failure=False returns the failed job instead of raising."""
    session = _FakeSession([_job_body("failed", state_message="disk full")])

    job = poll_worker_job(
        session=session,
        job_id="JOB1",
        poll_interval=0.01,
        max_wait=0.01,
        raise_on_failure=False,
    )

    assert job.state == WorkerJobState.FAILED
    assert job.state_message == "disk full"


def test_poll_worker_job_times_out_when_always_pending(monkeypatch: pytest.MonkeyPatch):
    """Test that exhausting max_attempts on a job stuck pending raises TimeoutError."""
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    session = _FakeSession([_job_body("inProgress"), _job_body("inProgress")])

    with pytest.raises(TimeoutError, match="JOB1"):
        poll_worker_job(
            session=session,
            job_id="JOB1",
            max_attempts=2,
            poll_interval=0.01,
            max_wait=0.01,
            job_description="Import",
        )

    assert session.calls == 2


def test_poll_worker_job_includes_job_description_in_failure_message():
    """Test that a custom job_description is threaded into the failure message."""
    session = _FakeSession([_job_body("failed", state_message="boom")])

    with pytest.raises(AlbertException, match="Combination generation JOB1 failed: boom"):
        poll_worker_job(
            session=session,
            job_id="JOB1",
            poll_interval=0.01,
            max_wait=0.01,
            job_description="Combination generation",
        )
