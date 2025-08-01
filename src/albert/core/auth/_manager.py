from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import Field

from albert.core.base import BaseAlbertModel


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
