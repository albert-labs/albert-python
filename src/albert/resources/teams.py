from enum import Enum
from typing import Any

from pydantic import Field

from albert.resources.base import BaseResource, SecurityClass
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.users import User
from albert.utils.types import BaseAlbertModel


class TeamRole(str, Enum):
    TEAM_OWNER = "TeamOwner"
    TEAM_VIEWER = "TeamViewer"


class TeamACL(BaseAlbertModel):
    id: str
    fgc: TeamRole


class TeamUsersPatchPayload(BaseAlbertModel):
    id: str
    data: list[dict[str, Any]]


class Team(BaseResource):
    id: str | None = Field(default=None, alias="albertId")
    name: str = Field(min_length=1, max_length=255)

    # Read-only fields
    security_class: SecurityClass | None = Field(default=None, alias="class", frozen=True)
    users: list[SerializeAsEntityLink[User]] | None = Field(
        default=None, alias="Users", frozen=True
    )
    acl: list[TeamACL] | None = Field(default=None, alias="ACL", frozen=True)
