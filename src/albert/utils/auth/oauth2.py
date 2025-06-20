import os
import webbrowser
from urllib.parse import urlencode

from albert.utils.auth._listener import start_local_http_server
from albert.utils.credentials import OAuthTokenInfo


class AlbertOAuthClient:
    """
    Implements Authorization Code Flow for Albert's OAuth implementation.

    Usage:
        oauth = AlbertOAuthClient(
            base_url="https://dev.albertinventdev.com",
            email="user@albertinvent.com",
        )
        token = oauth.authenticate()
        client = Albert.from_token(token)
    """

    def __init__(
        self,
        base_url: str,
        email: str,
    ):
        self.base_url = (
            base_url.rstrip("/") or os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com"
        )
        self.email = email
        self.token: OAuthTokenInfo | None = None

    def authenticate(
        self,
        minimum_port: int = 5000,
        maximum_port: int | None = None,
        tenant_id: str | None = None,
    ) -> OAuthTokenInfo:
        server, redirect_url = start_local_http_server(
            minimum_port=minimum_port, maximum_port=maximum_port
        )
        raw = {
            "email": self.email,
            "tenantId": tenant_id,
            # "redirect_uri": redirect_url,
        }

        params = {k: value for k, value in raw.items() if value is not None}
        sso_login_url = f"{self.base_url}/api/v3/login?{urlencode(params)}"
        webbrowser.open(sso_login_url)

        # Block here until one request arrives at localhost/?token=…
        server.handle_request()

        token = server.jwt
        print("Received token:", token)

        server.server_close()
        return token
