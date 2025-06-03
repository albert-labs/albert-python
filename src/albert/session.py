from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import albert
from albert.exceptions import handle_http_errors
from albert.utils.credentials import ClientCredentials, TokenManager


class AlbertSession(requests.Session):
    """
    A session that has a base URL, which is prefixed to all request URLs.

    Parameters
    ----------
    base_url : str
        The base URL to prefix to all requests. (e.g., "https://sandbox.albertinvent.com")
    retries : int
        The number of retries for failed requests. Defaults to 3.
    client_credentials : ClientCredentials | None
        The client credentials for programmatic authentication. Optional if token is provided.
    token : str | None
        The JWT token for authentication. Optional if client credentials are provided.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        client_credentials: ClientCredentials | None = None,
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

        if token is None and client_credentials is None:
            raise ValueError("Either client credentials or token must be specified.")

        self._provided_token = token
        self._token_manager = (
            TokenManager(base_url, client_credentials) if client_credentials is not None else None
        )

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
        if self._token_manager is not None:
            return self._token_manager.get_access_token()
        return self._provided_token

    def request(self, method: str, path: str, *args, **kwargs) -> requests.Response:
        self.headers["Authorization"] = f"Bearer {self._access_token}"
        full_url = urljoin(self.base_url, path) if not path.startswith("http") else path
        with handle_http_errors():
            response = super().request(method, full_url, *args, **kwargs)
            response.raise_for_status()
            return response
