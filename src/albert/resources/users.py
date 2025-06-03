from enum import Enum

from pydantic import EmailStr, Field

from albert.collections.locations import Location
from albert.collections.roles import Role
from albert.resources.base import BaseResource, MetadataItem
from albert.resources.identifiers import UserId
from albert.resources.serialization import SerializeAsEntityLink


class UserClass(str, Enum):
    """The ACL class level of the user"""

    GUEST = "guest"
    STANDARD = "standard"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"
    ADMIN = "admin"


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
