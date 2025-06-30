from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import albert
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.exceptions import handle_http_errors


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
        The number of automatic retries on failed requests (default is 3).
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
        retries: int | None = None,
    ):
        super().__init__()
        self.base_url = base_url
        self.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"albert-SDK V.{albert.__version__}",
            }
        )

        if token is None and auth_manager is None:
            raise ValueError("Either `token` or `auth_manager` must be specified.")

        self._auth_manager = auth_manager
        self._provided_token = token

        # Set up retry logic
        retries = retries if retries is not None else 3
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504, 403),
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

    def request(self, method: str, path: str, *args, **kwargs) -> requests.Response:
        self.headers["Authorization"] = f"Bearer {self._access_token}"
        full_url = urljoin(self.base_url, path) if not path.startswith("http") else path
        with handle_http_errors():
            response = super().request(method, full_url, *args, **kwargs)
            response.raise_for_status()
            return response
