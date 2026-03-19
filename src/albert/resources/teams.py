from typing import Any, Literal

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import TeamId, UserId
from albert.core.shared.models.base import BaseResource

TeamRole = Literal["TeamOwner", "TeamViewer"]


class TeamMember(BaseAlbertModel):
    """A user belonging to a team.

    Attributes
    ----------
    id : str
        The Albert user ID.
    name : str | None
        The display name of the user.
    role : TeamRole | None
        The team role. Must be ``"TeamOwner"`` or ``"TeamViewer"``.
    """

    id: UserId
    name: str | None = None
    role: TeamRole | None = Field(default=None, alias="fgc")


class Team(BaseResource):
    """Represents a Team on the Albert Platform.

    Attributes
    ----------
    id : str | None
        The Albert ID of the team. Set when the team is retrieved from Albert.
    name : str
        The name of the team.
    members : list[TeamMember] | None
        The members of the team with their names and roles.
    """

    id: TeamId | None = Field(default=None, alias="albertId")
    name: str = Field(min_length=1)
    members: list[TeamMember] | None = Field(default=None, alias="Users")

    @model_validator(mode="before")
    @classmethod
    def _merge_acl_into_users(cls, data: Any) -> Any:
        """Merge role information from the ACL list into the Users list."""
        if not isinstance(data, dict):
            return data
        users = data.get("Users")
        acl = data.get("ACL")
        if users and acl:
            role_map = {entry["id"]: entry.get("fgc") for entry in acl}
            for user in users:
                if user["id"] in role_map and "fgc" not in user:
                    user["fgc"] = role_map[user["id"]]
        return data
