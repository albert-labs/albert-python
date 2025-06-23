from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Field

from albert.collections.locations import Location
from albert.collections.roles import Role
from albert.core.base import BaseAlbertModel
from albert.core.models.common import BaseResource
from albert.core.models.enums import OrderBy, Status
from albert.core.models.identifiers import UserId
from albert.core.models.types import MetadataItem, SerializeAsEntityLink


class UserClass(str, Enum):
    """The ACL class level of the user"""

    GUEST = "guest"
    STANDARD = "standard"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"
    ADMIN = "admin"


class UserFilterType(str, Enum):
    ROLE = "role"


class User(BaseResource):
    """Represents a User on the Albert Platform

    Attributes
    ----------
    name : str
        The name of the user.
    id : str | None
        The Albert ID of the user. Set when the user is retrieved from Albert.
    location : Location | None
        The location of the user.
    email : EmailStr | None
        The email of the user.
    roles : list[Role]
        The roles of the user.
    user_class : UserClass
        The ACL class level of the user.
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
    """

    name: str
    id: UserId | None = Field(None, alias="albertId")
    location: SerializeAsEntityLink[Location] | None = Field(default=None, alias="Location")
    email: EmailStr = Field(default=None, alias="email")
    roles: list[SerializeAsEntityLink[Role]] = Field(
        max_length=1, default_factory=list, alias="Roles"
    )
    user_class: UserClass = Field(default=UserClass.STANDARD, alias="userClass")
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    def to_note_mention(self) -> str:
        """Convert the user to a note mention string.

        Returns
        -------
        str
            The note mention string.
        """
        return f"@{self.name}#{self.id}#"


class UserSearchRoleItem(BaseAlbertModel):
    roleId: str
    roleName: str


class UserSearchItem(BaseAlbertModel):
    """Partial user entity as returned by the search."""

    name: str
    id: UserId | None = Field(None, alias="albertId")
    email: EmailStr | None = Field(default=None, alias="email")
    user_class: UserClass = Field(default=UserClass.STANDARD, alias="userClass")
    last_login_time: datetime | None = Field(None, alias="lastLoginTime")
    location: str | None = None
    location_id: str | None = Field(None, alias="locationId")
    roles: list[UserSearchRoleItem] = Field(max_length=1, default_factory=list, alias="role")
    subscription: str | None = None


class UserFilterParams(BaseAlbertModel):
    """Structured filters for searching users, with API-compatible query parameter names."""

    limit: int = Field(default=50, ge=1, le=1000)
    offset: int | None = Field(default=None)
    text: str | None = Field(default=None)
    sort_by: str | None = Field(default=None, alias="sortBy")
    order_by: OrderBy = Field(default=OrderBy.DESCENDING, alias="order")
    roles: list[str] | None = None
    teams: list[str] | None = None
    locations: list[str] | None = None
    status: list[Status] | None = None
    user_id: list[str] | None = Field(default=None, alias="userId")
    subscription: list[str] | None = None
    search_fields: list[str] | None = Field(default=None, alias="searchFields")
    facet_text: str | None = Field(default=None, alias="facetText")
    facet_field: str | None = Field(default=None, alias="facetField")
    contains_field: list[str] | None = Field(default=None, alias="containsField")
    contains_text: list[str] | None = Field(default=None, alias="containsText")
    mentions: bool | None = None
