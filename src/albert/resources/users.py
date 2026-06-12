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
    """A user on the Albert platform.

    Attributes
    ----------
    name : str
        The display name of the user.
    id : str | None
        The Albert ID of the user.
    location : Location | None
        The physical location associated with the user.
    email : EmailStr | None
        The email address of the user.
    roles : list[Role]
        The roles assigned to the user (max one role).
    user_class : UserClass
        The ACL class level of the user. Defaults to ``standard``.
    metadata : dict[str, MetadataItem] | None
        Custom metadata attached to the user.
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
    """A role summary within a user search result.

    Attributes
    ----------
    roleId : str
        The Albert ID of the role.
    roleName : str
        The display name of the role.
    """

    roleId: str
    roleName: str


class UserSearchItem(BaseAlbertModel, HydrationMixin[User]):
    """Lightweight representation of a User returned from search.

    Attributes
    ----------
    name : str
        The display name of the user.
    id : UserId | None
        The Albert ID of the user.
    email : EmailStr | None
        The email address of the user.
    user_class : UserClass
        The ACL class level of the user.
    last_login_time : datetime | None
        The timestamp of the user's last login.
    location : str | None
        The location name associated with the user.
    location_id : str | None
        The Albert ID of the user's location.
    roles : list[UserSearchRoleItem]
        The roles assigned to the user (max one).
    subscription : str | None
        The subscription type of the user.
    """

    name: str
    id: UserId | None = Field(None, alias="albertId")
    email: EmailStr | None = Field(default=None, alias="email")
    user_class: UserClass = Field(default=UserClass.STANDARD, alias="userClass")
    last_login_time: datetime | None = Field(None, alias="lastLoginTime")
    location: str | None = None
    location_id: str | None = Field(None, alias="locationId")
    roles: list[UserSearchRoleItem] = Field(max_length=1, default_factory=list, alias="role")
    subscription: str | None = None
