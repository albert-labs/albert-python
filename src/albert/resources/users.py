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
    """The ACL class level of a user, setting a broad permission tier.

    Attributes
    ----------
    GUEST : str
        Most limited access; typically external or temporary users.
    STANDARD : str
        Default access level for regular users.
    TRUSTED : str
        Elevated access above standard users.
    PRIVILEGED : str
        High access level below full administrators.
    ADMIN : str
        Full administrative access to the tenant.
    """

    GUEST = "guest"
    STANDARD = "standard"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"
    ADMIN = "admin"


class UserFilterType(str, Enum):
    """The attribute a user query filters on.

    Attributes
    ----------
    ROLE : str
        Filter users by the roles they hold.
    """

    ROLE = "role"


class User(BaseResource):
    """An Albert user account: a person who can log in and act in the platform.

    A user has a name and email, an optional home
    [`Location`][albert.resources.locations.Location], and a set of
    [`Role`][albert.resources.roles.Role] objects that govern what they can do.
    The ``user_class`` sets a broad permission tier
    ([`UserClass`][albert.resources.users.UserClass]). Users are grouped into teams
    ([`Team`][albert.resources.teams.Team]), and are referenced across the
    platform, for example as the assignee of a Task or in an entity's ACL.

    !!! example
        ```python
        from albert.resources.users import User, UserClass
        user = User(
            name="Ada Lovelace",
            email="ada@example.com",
            user_class=UserClass.STANDARD,
        )
        ```

    Attributes
    ----------
    name : str
        The display name of the user.
    id : str | None
        The Albert User ID (format ``USR...``). Set once the user is registered
        in or retrieved from Albert.
    location : Location | None
        The user's home location.
    email : EmailStr | None
        The user's email address.
    roles : list[Role]
        The roles the user holds, which determine their permissions.
    user_class : UserClass
        The ACL class level of the user (broad permission tier).
    witnesser : bool | None
        Whether the user can act as a witness on tasks (only relevant when witnessing
        is enabled for the tenant).
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
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
    witnesser: bool | None = Field(default=None, alias="witnesser")
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
    """A role reference as returned within a user search result.

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
    """A partial user as returned by [`search`][albert.collections.users.UserCollection.search].

    Search returns these lightweight items for speed. Call
    `hydrate()` to fetch the full
    [`User`][albert.resources.users.User].

    Attributes
    ----------
    name : str
        The display name of the user.
    id : str | None
        The Albert User ID (format ``USR...``).
    email : EmailStr | None
        The user's email address.
    user_class : UserClass
        The ACL class level of the user (broad permission tier).
    last_login_time : datetime | None
        When the user most recently signed in.
    location : str | None
        The name of the user's home location.
    location_id : str | None
        The ID of the user's home location.
    roles : list[UserSearchRoleItem]
        The roles the user holds.
    subscription : str | None
        The user's subscription type.
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
