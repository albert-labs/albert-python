from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import httpx
import requests

from albert.core.logging import logger

if TYPE_CHECKING:
    from albert.resources.tasks import PropertyTask


class AlbertException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AlbertAuthError(AlbertException):
    """Raised when authentication fails (e.g., bad credentials, expired token)."""


def _restore_albert_http_error(cls: type, message: str) -> AlbertHTTPError:
    """Reconstruct an AlbertHTTPError from a pickled message string.

    Python's default exception pickling stores args and calls __init__(*args)
    on unpickle. AlbertHTTPError.__init__ expects a requests.Response, not a
    string, so the default path fails. This function bypasses __init__ and
    reconstructs the exception from the pre-formatted message alone.
    """
    exc = Exception.__new__(cls, message)
    exc.message = message
    exc.response = None
    return exc


class AlbertHTTPError(AlbertException):
    """Base class for all erors due to HTTP responses."""

    def __init__(self, response: requests.Response):
        message = self._format_message(response)
        super().__init__(message)
        self.response = response

    def __reduce__(self) -> tuple:
        return (_restore_albert_http_error, (type(self), self.message))

    @classmethod
    def _format_message(cls, response: requests.Response) -> str:
        try:
            payload = response.json()
            errors = payload.get("errors") or payload
        except ValueError:
            errors = response.text.strip()
        message = (
            f"{response.request.method} '{response.request.url}' failed with status code "
            f"{response.status_code} ({response.reason})."
        )
        return f"{message} Errors: {errors}" if errors else message


class AlbertClientError(AlbertHTTPError):
    """HTTP Error due to a client error response."""


class BadRequestError(AlbertClientError):
    """HTTP Error due to a 400 Bad Request response."""

    @classmethod
    def _format_message(cls, response: requests.Response) -> str:
        message = super()._format_message(response)
        message += f"\nBody:\n{response.request.body}"
        return message


class UnauthorizedError(AlbertClientError):
    """HTTP Error due to a 401 Unauthorized response."""


class ForbiddenError(AlbertClientError):
    """HTTP Error due to a 403 Forbidden response."""


class NotFoundError(AlbertClientError):
    """HTTP Error due to a 404 Not Found response."""


class AlbertServerError(AlbertHTTPError):
    """HTTP Error due to a server error response."""


class InternalServerError(AlbertServerError):
    """HTTP Error due to a 500 Internal Server Error response."""


class BadGateway(AlbertServerError):
    """HTTP Error due to a 502 Bad Gateway response."""


def _get_http_error_cls(status_code: int) -> type[AlbertHTTPError]:
    match status_code:
        case 400:
            return BadRequestError
        case 401:
            return UnauthorizedError
        case 403:
            return ForbiddenError
        case 404:
            return NotFoundError
        case 500:
            return InternalServerError
        case 502:
            return BadGateway
        case code if 400 <= code < 500:
            return AlbertClientError
        case code if 500 <= code < 600:
            return AlbertServerError
        case _:
            raise AlbertHTTPError


@contextlib.asynccontextmanager
async def handle_async_http_errors() -> AsyncIterator[None]:
    try:
        yield
    except httpx.HTTPStatusError as e:
        response = e.response
        try:
            payload = response.json()
            errors = payload.get("errors") or payload
        except Exception:
            errors = response.text.strip()
        reason = getattr(response, "reason_phrase", str(response.status_code))
        message = (
            f"{response.request.method} '{response.request.url}' failed with status code "
            f"{response.status_code} ({reason})."
        )
        if errors:
            message = f"{message} Errors: {errors}"
        error_cls = _get_http_error_cls(response.status_code)
        # Bypass AlbertHTTPError.__init__ (requires requests.Response), use
        # Exception.__new__ which sets exc.args and is safe in Python 3.12+.
        exc = Exception.__new__(error_cls, message)
        exc.message = message
        raise exc from e


@contextlib.contextmanager
def handle_http_errors() -> Iterator[None]:
    try:
        yield
    except requests.HTTPError as e:
        error_cls = _get_http_error_cls(e.response.status_code)
        albert_error = error_cls(e.response)
        # TODO: Enable debug logging via requests directly
        logger.debug("Albert HTTP Error %s", albert_error)
        raise albert_error from e


class CombinationGenerationError(AlbertException):
    """Raised when background combination generation fails for one or more task blocks.

    Raised by [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations]
    when ``wait=True`` and combination generation does not complete successfully on all blocks.

    Because the task itself has already been created on the platform, this exception
    carries the created task instance and details about which blocks failed. This allows
    callers to inspect the task state and retry generation for only the failed blocks
    using [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations].

    Attributes
    ----------
    task : PropertyTask or None
        The created Property task, re-fetched from the platform.
    failed_blocks : list[str]
        List of block IDs (format ``BLK...``) whose combination generation failed.
    job_states : dict[str, str]
        Mapping of block IDs to their final job states (e.g. ``{"BLK1": "successful", "BLK2": "failed"}``).

    !!! example
        ```python
        from albert import Albert
        from albert.exceptions import CombinationGenerationError
        from albert.resources.tasks import Block, PropertyTask

        client = Albert()
        try:
            task = client.tasks.create_with_combinations(task=prop_task)
        except CombinationGenerationError as err:
            print(f"Task {err.task.id} was created, but some blocks failed combination generation.")
            for block_id in err.failed_blocks:
                # Retry generation on the failed block:
                client.tasks.generate_block_combinations(
                    task_id=err.task.id,
                    block_id=block_id,
                )
        ```
    """

    task: PropertyTask | None
    failed_blocks: list[str]
    job_states: dict[str, str]

    def __init__(
        self,
        message: str,
        *,
        task: PropertyTask | None = None,
        failed_blocks: list[str] | None = None,
        job_states: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.task = task
        self.failed_blocks = failed_blocks or []
        self.job_states = job_states or {}
