from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from pydantic import Field

from albert.core.auth._manager import AuthManager, OAuthTokenInfo
from albert.core.base import BaseAlbertModel
from albert.exceptions import AlbertAuthError, handle_http_errors
from albert.utils._auth import default_albert_base_url


class AlbertSSOTokenExchange(BaseAlbertModel, AuthManager):
    """
    Auth manager for server-to-server OIDC token exchange with the Albert API.

    Exchanges an OpenID Connect (OIDC) ID token for an Albert access token without
    any browser interaction. Suitable for custom applications that already authenticate
    users via an OIDC-compliant identity provider.

    The identity provider must emit the ``preferred_username`` claim in the ID token,
    which Albert uses to look up the corresponding user. Most enterprise IdPs include
    this claim by default; see the authentication guide for provider-specific notes.

    Requires tenant-level OIDC configuration: the OpenID Connect ``aud`` claim
    must be registered with Albert for the target tenant. Contact Albert support
    to enable this feature.

    Parameters
    ----------
    base_url : str
        The base URL of the Albert API.
    subdomain : str
        The tenant subdomain (e.g. ``"mycompany"``).
    oidc_token_provider : Callable[[], str]
        A zero-argument callable that returns a fresh OIDC ID token on demand.
        Called on the first request and on every token renewal.
        A lambda returning a static string works for short-lived sessions.

    Usage
    -----
    ```python
    def get_oidc_token() -> str:
        # Acquire an ID token from your identity provider
        ...

    auth = AlbertSSOTokenExchange(
        base_url="https://mycompany.albertinvent.com",
        subdomain="mycompany",
        oidc_token_provider=get_oidc_token,
    )
    client = Albert(auth_manager=auth)
    ```
    """

    base_url: str = Field(default_factory=default_albert_base_url)
    subdomain: str
    oidc_token_provider: Callable[[], str]

    @property
    def exchange_url(self) -> str:
        return urljoin(self.base_url, "/api/v3/login/sso/exchange")

    def _exchange(self) -> None:
        with handle_http_errors():
            response = requests.post(
                self.exchange_url,
                json={"jwt": self.oidc_token_provider(), "subdomain": self.subdomain},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        access_token = data.get("jwt")
        refresh_token = data.get("refreshtoken")
        if not access_token or not refresh_token:
            raise AlbertAuthError(
                "SSO exchange failed: unexpected response from server. "
                f"Expected 'jwt' and 'refreshtoken' fields, got: {list(data.keys())}"
            )
        expires_in = data.get("expires_in", 3300)  # fallback: 55 min until backend ships field
        self._token_info = OAuthTokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
        self._refresh_time = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in) - timedelta(minutes=1)
        )

    def get_access_token(self) -> str:
        """Return a valid Albert access token, re-exchanging via the OIDC provider if needed."""
        if self._requires_refresh():
            self._exchange()
        return self._token_info.access_token
