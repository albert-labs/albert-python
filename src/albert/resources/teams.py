from enum import Enum

from pydantic import Field

from albert.resources.acls import ACL
from albert.resources.base import BaseResource, SecurityClass
from albert.resources.users import User


class TeamRole(str, Enum):
    TEAM_OWNER = "TeamOwner"
    TEAM_VIEWER = "TeamViewer"


class Team(BaseResource):
    id: str | None = Field(default=None, alias="albertId")
    name: str = Field(min_length=1, max_length=255)
    team_class: SecurityClass | None = Field(default=None, alias="class")
    user: list[User] | None = Field(default=None)
    acl: list[ACL] | None = Field(default=None)
