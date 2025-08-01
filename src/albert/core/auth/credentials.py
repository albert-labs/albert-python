from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urljoin

import requests
from pydantic import Field, SecretStr

from albert.core.auth._manager import AuthManager, OAuthTokenInfo
from albert.core.base import BaseAlbertModel
from albert.exceptions import handle_http_errors
from albert.utils._auth import default_albert_base_url


class AlbertClientCredentials(BaseAlbertModel, AuthManager):
    """
    Client credentials manager for programmatic OAuth2 access to the Albert API.

    This class implements the OAuth2 Client Credentials flow, allowing automated
    (non-interactive) systems to authenticate securely using a client ID and secret.

    Attributes
    ----------
    id : str
        The client ID used for authentication.
    secret : SecretStr
        The client secret used for authentication.
    base_url : str
        The base URL of the Albert API.

    Usage
    -----
    ```
    creds = AlbertClientCredentials(
        id="your-client-id",
        secret=SecretStr("your-client-secret"),
        base_url="https://app.albertinvent.com",
    )
    client = Albert(auth_manager=creds)
    client.roles.get_all()
    ```
    """

    id: str
    secret: SecretStr
    base_url: str = Field(default_factory=default_albert_base_url)

    @property
    def oauth_token_url(self) -> str:
        """Return the full URL to the OAuth token endpoint."""
        oauth_token_path: str = "/api/v3/login/oauth/token"
        return urljoin(self.base_url, oauth_token_path)

    @classmethod
    def from_env(
        cls,
        *,
        base_url_env: str = "ALBERT_BASE_URL",
        client_id_env: str = "ALBERT_CLIENT_ID",
        client_secret_env: str = "ALBERT_CLIENT_SECRET",
    ) -> AlbertClientCredentials | None:
        """
        Create `AlbertClientCredentials` from environment variables.

        Returns None if any of the required environment variables are missing.

        Parameters
        ----------
        base_url_env : str
            Name of the environment variable containing the base URL
            (defaults to "ALBERT_BASE_URL").
        client_id_env : str
            Name of the environment variable containing the client ID
            (defaults to "ALBERT_CLIENT_ID").
        client_secret_env : str
            Name of the environment variable containing the client secret
            (defaults to "ALBERT_CLIENT_SECRET").

        Returns
        -------
        AlbertClientCredentials | None
            The credentials instance if all environment variables are present;
            otherwise, None.
        """
        base_url = os.getenv(base_url_env)
        client_id = os.getenv(client_id_env)
        client_secret = os.getenv(client_secret_env)

        if client_id and client_secret and base_url:
            return cls(
                id=client_id,
                secret=SecretStr(client_secret),
                base_url=base_url,
            )

    def _request_access_token(self) -> None:
        """Request and store a new access token using client credentials."""
        payload = CreateOAuthToken(
            client_id=self.id,
            client_secret=self.secret.get_secret_value(),
        )
        with handle_http_errors():
            response = requests.post(
                self.oauth_token_url,
                data=payload.model_dump(mode="json"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        self._token_info = OAuthTokenInfo(**response.json())
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


class CreateOAuthToken(BaseAlbertModel):
    grant_type: Literal["client_credentials"] = "client_credentials"
    client_id: str
    client_secret: str
