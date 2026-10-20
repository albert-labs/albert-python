import contextvars
import json
from collections.abc import Mapping
from enum import Enum
from urllib.parse import quote, urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import albert
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.exceptions import handle_http_errors

DEFAULT_TIMEOUT = (10, 300)
"""Default (connect, read) timeout in seconds applied to every call."""

RETRYABLE_STATUSES = (403, 429, 500, 502, 503, 504)
"""Statuses retried with exponential backoff."""

_retry_safe_request: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "retry_safe_request", default=False
)
"""Set for the duration of a call opted in to retries regardless of method."""


class _AlbertRetry(Retry):
    """Retry policy that retries throttled and retry-safe calls for every HTTP method.

    urllib3's default policy retries only idempotent methods. A throttled call
    (status 429) is safe to retry for any method because the server rejected it
    before processing, so 429 is retried for all methods. Calls marked retry-safe
    (read-only operations issued with a non-idempotent method, such as searches)
    retry every ``status_forcelist`` status. All other calls keep the default
    idempotent-only behavior.
    """

    def is_retry(self, method: str, status_code: int, has_retry_after: bool = False) -> bool:
        if status_code == 429:
            return True
        if (
            _retry_safe_request.get(False)
            and self.status_forcelist
            and status_code in self.status_forcelist
        ):
            return True
        return super().is_retry(method, status_code, has_retry_after)


class AlbertSession(requests.Session):
    """
    A session that has a base URL, which is prefixed to all request URLs.

    Parameters
    ----------
    base_url : str
        The base URL to prefix to all relative request paths (e.g., "https://app.albertinvent.com").
    token : str | None, optional
        A static JWT token for authentication. Ignored if `auth_manager` is provided.
    auth_manager : AlbertClientCredentials | AlbertSSOClient, optional
        An authentication manager used to dynamically fetch and refresh tokens.
        If provided, it overrides `token`.
    retries : int, optional
        The number of automatic retries on failed or throttled calls (default is 3).
        Throttled calls are retried for every method; transient server errors are
        retried for idempotent methods only, unless the call is marked retry-safe
        (read-only operations such as searches). A ``Retry-After`` hint from the
        server is honored.
    timeout : float | tuple[float, float], optional
        Default timeout in seconds applied to every call. Accepts a single
        float (applied to both connect and read) or a ``(connect, read)`` tuple.
        Defaults to ``DEFAULT_TIMEOUT`` (10 s connect, 300 s read). Pass ``None``
        for no timeout. A per-call ``timeout`` always takes precedence.
    headers : Mapping[str, str], optional
        Extra headers applied to every request made through this session, for
        example a caller-supplied correlation or audit header. Merged over the
        session defaults, matching header names case-insensitively, so a key
        given here replaces ``Content-Type``, ``Accept``, or ``User-Agent``
        rather than being sent alongside it. ``Authorization`` is set per
        request from the session's own credentials and cannot be overridden
        here.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
        retries: int | None = None,
        timeout: float | tuple[float, float] | None = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__()
        self.base_url = base_url
        self._timeout = timeout
        self.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"albert-SDK V.{albert.__version__}",
            }
        )
        if headers:
            self.headers.update(headers)

        if token is None and auth_manager is None:
            raise ValueError("Either `token` or `auth_manager` must be specified.")

        self._auth_manager = auth_manager
        self._provided_token = token

        # Set up retry logic
        retries = retries if retries is not None else 3
        retry = _AlbertRetry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.3,
            status_forcelist=RETRYABLE_STATUSES,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    @property
    def _access_token(self) -> str | None:
        """Get the access token from the token manager or provided token."""
        if self._auth_manager is not None:
            return self._auth_manager.get_access_token()
        return self._provided_token

    def request(
        self, method: str, path: str, *args, retry_safe: bool = False, **kwargs
    ) -> requests.Response:
        # Send auth via per-request headers: mutating self.headers is not safe when
        # the session is shared across threads. Applied last so neither a
        # per-request header nor a session default can displace it.
        headers = dict(kwargs.pop("headers", None) or {})
        headers["Authorization"] = f"Bearer {self._access_token}"
        kwargs["headers"] = headers
        kwargs.setdefault("timeout", self._timeout)
        full_url = urljoin(self.base_url, path) if not path.startswith("http") else path
        params = self._encode_query_params(kwargs.pop("params", None) or {})
        # The requests library internally uses urllib.parse.urlencode() with the quote_via parameter set to quote_plus, which breaks CAS pagination.
        # Encoding parameters manually (via quote) to avoid this issue.
        if params:
            qs = urlencode(params, doseq=True, quote_via=quote)
            full_url = f"{full_url}?{qs}"

        marker = _retry_safe_request.set(retry_safe)
        try:
            with handle_http_errors():
                response = super().request(method, full_url, *args, **kwargs)
                response.raise_for_status()
                return response
        finally:
            _retry_safe_request.reset(marker)

    def _encode_query_params(self, params: dict) -> dict:
        """Encode and clean up query parameters for the request."""

        def convert(v):
            if isinstance(v, bool):
                return json.dumps(v)
            if isinstance(v, Enum):
                return v.value
            if isinstance(v, list) and all(isinstance(i, Enum) for i in v):
                return [i.value for i in v]
            return v

        return {k: convert(v) for k, v in params.items() if v is not None}
