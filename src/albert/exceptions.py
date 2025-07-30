import contextlib
from collections.abc import Iterator

import requests

from albert.core.logging import logger


class AlbertException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AlbertAuthError(AlbertException):
    """Raised when authentication fails (e.g., bad credentials, expired token)."""


class AlbertHTTPError(AlbertException):
    """Base class for all erors due to HTTP responses."""

    def __init__(self, response: requests.Response):
        message = self._format_message(response)
        super().__init__(message)
        self.response = response

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
