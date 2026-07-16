from typing import Any, Literal

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import TeamId, UserId
from albert.core.shared.models.base import BaseResource

TeamRole = Literal["TeamOwner", "TeamViewer"]


class TeamMember(BaseAlbertModel):
    """A user's membership in a team, pairing a user with their team role.

    Attributes
    ----------
    id : str
        The Albert User ID (format ``USR...``) of the member.
    name : str | None
        The display name of the user.
    role : TeamRole | None
        The member's role within the team: ``"TeamOwner"`` (can manage the
        team) or ``"TeamViewer"`` (read access). Defaults to ``"TeamViewer"``
        when unset.

    Examples
    --------
    ```python
    from albert.resources.teams import TeamMember
    member = TeamMember(id="USR12", role="TeamOwner")
    ```
    """

    id: UserId
    name: str | None = None
    role: TeamRole | None = Field(default=None, alias="fgc")


class Team(BaseResource):
    """A named group of users on the Albert platform.

    Teams share access: entity ACLs and Task assignments can reference a whole
    team rather than individual users. Each member is a
    [`TeamMember`][albert.resources.teams.TeamMember] pairing a
    [`User`][albert.resources.users.User] with a team role.

    Attributes
    ----------
    id : str | None
        The Albert Team ID (format ``TEM...``). Set once the team is registered
        in or retrieved from Albert.
    name : str
        The display name of the team.
    members : list[TeamMember] | None
        The members of the team, each with their name and team role.

    Examples
    --------
    ```python
    from albert.resources.teams import Team, TeamMember
    team = Team(
        name="Coatings R&D",
        members=[TeamMember(id="USR12", role="TeamOwner")],
    )
    ```
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
