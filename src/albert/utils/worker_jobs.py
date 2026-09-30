"""Utilities for working with background worker jobs."""

from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from albert.core.logging import logger
from albert.core.session import AlbertSession
from albert.exceptions import AlbertException
from albert.resources.worker_jobs import (
    WORKER_JOB_PENDING_STATES,
    WorkerJob,
    WorkerJobState,
)

DEFAULT_WORKER_JOB_POLL_INTERVAL = 2.0
DEFAULT_WORKER_JOB_MAX_ATTEMPTS = 60
DEFAULT_WORKER_JOB_MAX_WAIT = 10.0


class _WorkerJobPending(Exception):
    """Internal sentinel exception indicating the worker job is still running."""


def poll_worker_job(
    *,
    session: AlbertSession,
    job_id: str,
    max_attempts: int = DEFAULT_WORKER_JOB_MAX_ATTEMPTS,
    poll_interval: float = DEFAULT_WORKER_JOB_POLL_INTERVAL,
    max_wait: float = DEFAULT_WORKER_JOB_MAX_WAIT,
    raise_on_failure: bool = True,
    job_description: str = "Worker job",
) -> WorkerJob:
    """Poll a worker job until it reaches a terminal state.

    Parameters
    ----------
    session : AlbertSession
        Authenticated session for platform requests.
    job_id : str
        The worker job identifier (format ``JOB...``), such as ``block.job_id``
        or ``worker_job.albert_id``.
    max_attempts : int, optional
        Maximum number of polling attempts, by default 60.
    poll_interval : float, optional
        Minimum wait time in seconds between attempts, by default 2.0.
    max_wait : float, optional
        Maximum wait time in seconds between attempts, by default 10.0.
    raise_on_failure : bool, optional
        Whether to raise an exception if the job finishes with state other than
        ``successful``, by default True.
    job_description : str, optional
        Human-readable description for logging.

    Returns
    -------
    WorkerJob
        The completed worker job.

    Raises
    ------
    TimeoutError
        If the job does not complete within the retry window.
    AlbertException
        If ``raise_on_failure`` is True and the job failed or was cancelled.
    """

    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=poll_interval, max=max_wait),
        reraise=True,
    )
    def _poll() -> WorkerJob:
        status_response = session.get(f"/api/v3/worker-jobs/{job_id}")
        current_job = WorkerJob.model_validate(status_response.json())
        state = current_job.state

        if state in WORKER_JOB_PENDING_STATES:
            logger.info("%s %s in progress (state: %s)", job_description, job_id, state)
            raise _WorkerJobPending()
        return current_job

    try:
        worker_job = _poll()
    except _WorkerJobPending as exc:
        raise TimeoutError(
            f"{job_description} {job_id} did not complete within the retry window."
        ) from exc

    if raise_on_failure and worker_job.state != WorkerJobState.SUCCESSFUL:
        message = worker_job.state_message or f"job state is {worker_job.state.value}"
        raise AlbertException(f"{job_description} {job_id} failed: {message}")

    return worker_job
