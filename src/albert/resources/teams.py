from enum import Enum

from pydantic import Field

from albert.resources.base import BaseResource, SecurityClass
from albert.resources.users import User
from albert.utils.types import BaseAlbertModel


class TeamRole(str, Enum):
    TEAM_OWNER = "TeamOwner"
    TEAM_VIEWER = "TeamViewer"


class TeamACL(BaseAlbertModel):
    id: str
    fgc: TeamRole


class Team(BaseResource):
    id: str | None = Field(default=None, alias="albertId")
    name: str = Field(min_length=1, max_length=255)
    security_class: SecurityClass | None = Field(default=None, alias="class")
    users: list[User] | None = Field(default=None, alias="Users")
    acl: list[TeamACL] | None = Field(default=None, alias="ACL")
