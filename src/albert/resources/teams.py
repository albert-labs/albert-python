from pydantic import Field

from albert.resources.base import BaseResource, EntityLinkConvertible, SecurityClass
from albert.resources.users import User


class Team(BaseResource, EntityLinkConvertible):
    # do all fields from the DWH tables go here?
    id: str | None = Field(default=None, alias="albertId")
    name: str = Field(min_length=1, max_length=255)
    team_class: SecurityClass | None = Field(default=None, alias="class")
    user: list[User] | None = Field(default=None)
    # acl: None
