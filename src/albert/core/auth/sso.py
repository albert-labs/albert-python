import os
import webbrowser
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin

import requests
from pydantic import Field

from albert.core.auth._listener import start_local_http_server
from albert.core.auth._manager import AuthManager, OAuthTokenInfo
from albert.core.base import BaseAlbertModel
from albert.exceptions import handle_http_errors


class AlbertSSOClient(BaseAlbertModel, AuthManager):
    """
    OAuth2 client for performing Authorization Code Flow with the Albert API.

    This client opens a browser-based SSO login flow and handles token acquisition
    and refresh using a local redirect server.

    If `base_url` is not provided, it defaults to the value of the environment
    variable "ALBERT_BASE_URL" or "https://app.albertinvent.com".

    Attributes
    ----------
    base_url : str
        The base URL of the Albert API.
    email : str
        The email address used for initiating the login flow.

    Usage
    -----
    >>> oauth = AlbertOAuthClient(
    ...     email="user@example.com",
    ... )
    >>> oauth.authenticate()
    >>> client = Albert(auth_manager=oauth)
    >>> client.roles.get_all()
    """

    base_url: str = Field(
        default_factory=lambda: (
            os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com"
        ).rstrip("/")
    )
    email: str

    def authenticate(
        self,
        minimum_port: int = 5000,
        maximum_port: int | None = None,
        tenant_id: str | None = None,
    ) -> OAuthTokenInfo:
        """
        Launch an interactive browser-based SSO login and return an OAuth token.

        This method starts a temporary local HTTP server, opens the SSO login URL
        in the default browser, and waits for the authentication redirect to capture
        the refresh token.

        Parameters
        ----------
        minimum_port : int, optional
            The starting port to attempt for the local HTTP redirect server (default is 5000).
        maximum_port : int | None, optional
            The maximum port to try if the `minimum_port` is unavailable. If None, only the
            minimum port will be tried.
        tenant_id : str | None, optional
            Optional tenant ID to scope the SSO login request.

        Returns
        -------
        OAuthTokenInfo
            The initial token info containing the refresh token.
        """
        server, port = start_local_http_server(
            minimum_port=minimum_port, maximum_port=maximum_port
        )
        raw = {
            "source": "sdk",
            "email": self.email,
            "port": port,
            "tenantId": tenant_id,
        }

        params = {k: value for k, value in raw.items() if value is not None}
        sso_login_url = f"{self.base_url}/api/v3/login?{urlencode(params)}"
        webbrowser.open(sso_login_url)

        # Block here until one request arrives at localhost:port/?token=…
        server.handle_request()

        refresh_token = server.token
        server.server_close()

        self._token_info = OAuthTokenInfo(refresh_token=refresh_token)
        return self._token_info

    @property
    def refresh_token_url(self) -> str:
        refresh_token_path = "/api/v3/login/refresh"
        return urljoin(self.base_url, refresh_token_path)

    def _request_access_token(self) -> None:
        """Request and store a new access token using refresh-token."""
        payload = {"refreshtoken": self._token_info.refresh_token}
        with handle_http_errors():
            response = requests.post(
                self.refresh_token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()[0]

        self._token_info = OAuthTokenInfo(
            access_token=data["jwt"], expires_in=data["exp"], refresh_token=data["refreshToken"]
        )
        self._refresh_time = (
            datetime.now(timezone.utc)
            + timedelta(seconds=self._token_info.expires_in)
            - timedelta(minutes=1)  # Buffer to avoid token expiration
        )

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing it if needed."""
        if self._requires_refresh():
            self._request_access_token()
        return self._token_info.access_token
