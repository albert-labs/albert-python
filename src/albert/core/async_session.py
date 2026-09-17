from __future__ import annotations

import httpx

import albert
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.exceptions import handle_async_http_errors


class AsyncAlbertSession:
    """
    Async HTTP session for the Albert API backed by ``httpx.AsyncClient``.

    Authentication is resolved synchronously via ``get_access_token()`` on each
    request.  Token refresh only blocks the event loop on the rare occasion that
    the cached token has expired; all other calls return immediately.

    Parameters
    ----------
    base_url : str
        The base URL of the Albert API.
    token : str | None, optional
        A static JWT token. Ignored when ``auth_manager`` is provided.
    auth_manager : AlbertClientCredentials | AlbertSSOClient | None, optional
        An authentication manager for OAuth2 token refresh. Overrides ``token``.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
    ):
        if token is None and auth_manager is None:
            raise ValueError("Either `token` or `auth_manager` must be specified.")

        self._auth_manager = auth_manager
        self._provided_token = token
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"albert-SDK V.{albert.__version__}",
            },
        )

    @property
    def _access_token(self) -> str | None:
        if self._auth_manager is not None:
            return self._auth_manager.get_access_token()
        return self._provided_token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"
        async with handle_async_http_errors():
            response = await self._client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
        return response

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Send a GET request."""
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Send a POST request."""
        return await self._request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        """Send a PATCH request."""
        return await self._request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Send a DELETE request."""
        return await self._request("DELETE", path, **kwargs)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncAlbertSession:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
