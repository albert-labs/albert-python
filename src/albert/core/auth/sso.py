import webbrowser
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin

import requests
from pydantic import Field

from albert.core.auth._listener import local_http_server
from albert.core.auth._manager import AuthManager, OAuthTokenInfo
from albert.core.base import BaseAlbertModel
from albert.core.logging import logger
from albert.exceptions import AlbertAuthError, handle_http_errors
from albert.utils._auth import default_albert_base_url


class AlbertSSOClient(BaseAlbertModel, AuthManager):
    """
    OAuth2 client for performing Authorization Code Flow with the Albert API.

    This client opens a browser-based SSO login flow and handles token acquisition
    and refresh using a local redirect server.

    If `base_url` is not provided, it defaults to the value of the environment
    variable `ALBERT_BASE_URL` or `https://app.albertinvent.com`.

    !!! important
        You **must call** `.authenticate()` before passing this client to `Albert(auth_manager=...)`
        to ensure the token is acquired and ready for use.

    Attributes
    ----------
    base_url : str
        The base URL of the Albert API.
    email : str
        The email address used for initiating the login flow.

    Usage
    -----
    ```
    oauth = AlbertSSOClient(
        email="user@example.com",
    )
    oauth.authenticate()
    client = Albert(auth_manager=oauth)
    client.roles.get_all()
    ```
    """

    base_url: str = Field(default_factory=default_albert_base_url)
    email: str

    def authenticate(
        self,
        minimum_port: int = 5000,
        maximum_port: int | None = None,
        tenant_id: str | None = None,
        timeout: int = 5,
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
        self._validate_email(email=self.email, tenant_id=tenant_id)
        with local_http_server(
            minimum_port=minimum_port,
            maximum_port=maximum_port,
            timeout=timeout,
        ) as (server, port):
            login_url = self._build_login_url(port=port, tenant_id=tenant_id)
            webbrowser.open(login_url)
            # Block here until one request arrives at localhost:port/?token=…
            server.handle_request()
            refresh_token = server.token
            if not refresh_token:
                raise AlbertAuthError("SSO Login failed! Please try again.")

        self._token_info = OAuthTokenInfo(
            refresh_token=refresh_token,
            tenant_id=tenant_id.upper() if tenant_id else None,
        )
        return self._token_info

    @property
    def refresh_token_url(self) -> str:
        refresh_token_path = "/api/v3/login/refresh"
        return urljoin(self.base_url, refresh_token_path)

    def _request_access_token(self) -> None:
        """Request and store a new access token using refresh-token."""
        with handle_http_errors():
            response = requests.post(
                self.refresh_token_url,
                json={"refreshtoken": self._token_info.refresh_token},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            tokens = response.json()

        tenant_id = self._token_info.tenant_id
        tenant_id = tenant_id.upper() if tenant_id else None

        if tenant_id:
            try:
                token = next(t for t in tokens if t["tenantId"] == tenant_id)
            except StopIteration as e:
                msg = "User not found or access denied."
                raise AlbertAuthError(f"SSO Login failed: {msg}") from e
        else:
            token = tokens[0]
            if len(tokens) > 1:
                logger.warning(
                    "User %s has access to multiple tenants but no `tenant_id` was specified. "
                    "Defaulting to tenant %s. To avoid ambiguity, pass `tenant_id` to `authenticate()` or `from_sso()`. "
                    "Available tenants: %s",
                    self.email,
                    token["tenantId"],
                    [t["tenantId"] for t in tokens],
                )

        self._token_info = OAuthTokenInfo(
            access_token=token["jwt"],
            expires_in=token["exp"],
            refresh_token=token["refreshToken"],
            tenant_id=token["tenantId"],
        )

        self._refresh_time = (
            datetime.now(timezone.utc)
            + timedelta(seconds=self._token_info.expires_in)
            - timedelta(minutes=1)  # Buffer to avoid token expiration
        )

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing it if needed."""
        if not self._token_info or not self._token_info.refresh_token:
            raise AlbertAuthError("Client not authenticated. Call `.authenticate()` first.")
        if self._requires_refresh():
            self._request_access_token()
        return self._token_info.access_token

    def _build_login_url(self, *, port: int, tenant_id: str | None) -> str:
        """Build sso login URL."""
        path = "/api/v3/login"
        raw = {
            "source": "sdk",
            "email": self.email,
            "port": port,
            "tenantId": tenant_id,
        }

        params = {k: value for k, value in raw.items() if value is not None}
        query = urlencode(params)
        return f"{urljoin(self.base_url, path)}?{query}"

    def _validate_email(self, *, email: str, tenant_id: str | None) -> None:
        """
        Validate whether the given user has access to the tenant.

        Parameters
        ----------
        email : str
            Email to validate.
        tenant_id : str | None
            Tenant to scope the SSO login check.

        Raises
        ------
        AlbertAuthError
            If the user does not have access or the response is unexpected.
        """
        path = "/api/v3/login"
        raw = {
            "email": email,
            "tenantId": tenant_id,
        }

        params = {k: v for k, v in raw.items() if v is not None}
        url = f"{urljoin(self.base_url, path)}?{urlencode(params)}"

        try:
            response = requests.get(url, allow_redirects=False, timeout=5)
        except requests.RequestException as e:
            raise AlbertAuthError(f"SSO Login failed: {e}") from e

        if response.status_code == 302:
            return  # OK

        if response.status_code == 404:
            msg = "User not found or access denied."
            raise AlbertAuthError(f"SSO Login failed: {msg}")

        raise AlbertAuthError(
            f"Unexpected response from SSO Login: {response.status_code} {response.reason}"
        )
