from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import jwt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import albert
from albert.exceptions import handle_http_error
from albert.utils.client_credentials import ClientCredentials


def get_token_refresh_time(token: str, *, buffer: timedelta | None) -> datetime:
    claims = jwt.decode(token, options={"verify_signature": False})
    try:
        exp_time = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    except ValueError:
        # exp is in millis, not seconds, so datetime fails
        exp_time = datetime.fromtimestamp(claims["exp"] / 1000, tz=timezone.utc)
    buffer = buffer or timedelta(seconds=0)
    return exp_time - buffer


class AlbertSession(requests.Session):
    """
    A session that has a base URL, which is prefixed to all request URLs.

    Parameters
    ----------
    base_url : str
        The base URL to prefix to all requests.
    retries : int
        The number of retries for failed requests. Defaults to 3.
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

        self._client_credentials = client_credentials
        self._access_token = None
        self._access_token_refresh_time = None

        if self._client_credentials is not None:
            self._refresh_token()
        elif token is not None:
            self._set_access_token(token)
        else:
            raise ValueError("Either client credentials or token must be specified.")

        # Set up retry logic
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504, 403),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def _set_access_token(self, token: str) -> None:
        self._access_token = token
        self._access_token_refresh_time = get_token_refresh_time(
            self._access_token, buffer=timedelta(minutes=1)
        )
        self.headers["Authorization"] = f"Bearer {self._access_token}"

    def _get_client_token(self) -> str:
        path = "/api/v3/login/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_credentials.id,
            "client_secret": self._client_credentials.secret.get_secret_value(),
        }
        response = self._request(
            "POST",
            path,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.json()["access_token"]

    def _requires_refresh(self) -> bool:
        return datetime.now(timezone.utc) > self._access_token_refresh_time

    def _refresh_token(self) -> None:
        # TODO: Implement using refresh token once it is working
        token = self._get_client_token()
        self._set_access_token(token)

    def _request(self, method: str, path: str, *args, **kwargs) -> requests.Response:
        full_url = urljoin(self.base_url, path) if not path.startswith("http") else path
        response = super().request(method, full_url, *args, **kwargs)
        handle_http_error(response)
        return response

    def request(self, method: str, path: str, *args, **kwargs) -> requests.Response:
        if self._requires_refresh() and self._client_credentials is not None:
            self._refresh_token()
        return self._request(method, path, *args, **kwargs)
