import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import Field

from albert.core.base import BaseAlbertModel

if TYPE_CHECKING:
    from pypac.resolver import ProxyResolver


class OAuthTokenInfo(BaseAlbertModel):
    issued_token_type: str = Field(default="access_token")
    token_type: str = Field(default="Bearer")
    access_token: str = Field(default="")
    refresh_token: str
    expires_in: int = Field(default=0)
    tenant_id: str | None = Field(default=None)


class AuthManager(ABC):
    """
    Abstract base class for all authentication managers.
    Provides a common interface for retrieving and refreshing access tokens.
    """

    _token_info: OAuthTokenInfo | None = None
    _refresh_time: datetime | None = None
    # Class-level lock: serializes token refresh across threads sharing a manager
    _refresh_lock: threading.Lock = threading.Lock()
    _pac_proxy_resolver: "ProxyResolver | None" = None

    def _proxies_for(self, url: str) -> dict[str, str | None] | None:
        """Return the proxy configuration for a call to the given URL.

        A PAC file decides per call; otherwise the manager's static proxies apply.
        """
        pac_url = getattr(self, "pac_url", None)
        if pac_url is None:
            proxies = getattr(self, "proxies", None)
            return dict(proxies) if proxies else None
        # Deferred: albert.core.session imports the auth managers for typing.
        from albert.core.session import _load_pac_proxy_resolver, _pac_proxies_for

        if self._pac_proxy_resolver is None:
            self._pac_proxy_resolver = _load_pac_proxy_resolver(pac_url)
        return _pac_proxies_for(self._pac_proxy_resolver, url)

    def _requires_refresh(self) -> bool:
        return (
            self._token_info is None
            or self._refresh_time is None
            or datetime.now(timezone.utc) > self._refresh_time
        )

    @abstractmethod
    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        ...
