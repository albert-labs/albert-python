from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import UserId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.locations import Location
from albert.resources.roles import Role


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


class UserSearchItem(BaseAlbertModel, HydrationMixin[User]):
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
