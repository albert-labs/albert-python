from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import TeamId, UserId
from albert.core.utils import ensure_list
from albert.exceptions import AlbertException
from albert.resources.teams import Team, TeamMember
from albert.resources.users import User


class TeamCollection(BaseCollection):
    """TeamCollection manages Team entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for team API requests.

    Methods
    -------
    get_all(name, exact_match, created_by, updated_by, user_id, max_items) -> Iterator[Team]
        Lists all teams with optional filters.
    get_by_id(id) -> Team
        Retrieves a team by its ID.
    create(name, members) -> Team
        Creates a new team, optionally with initial members.
    update(team) -> Team
        Updates a team's name and membership.
    delete(id) -> None
        Deletes a team by its ID.
    add_users(id, members) -> Team
        Adds users to a team.
    remove_users(id, users) -> Team
        Removes users from a team.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize the TeamCollection.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TeamCollection._api_version}/teams"

    def _resolve_user_id(self, user: User | UserId) -> str:
        """Extract a user ID string from a User object or raw ID."""
        if isinstance(user, User):
            return user.id
        return user

    def get_all(
        self,
        *,
        name: str | list[str] | None = None,
        exact_match: bool = True,
        created_by: str | None = None,
        updated_by: str | None = None,
        user_id: str | list[str] | None = None,
        max_items: int | None = None,
    ) -> Iterator[Team]:
        """List all teams with optional filters.

        Parameters
        ----------
        name : str or list[str], optional
            Filter teams by one or more names.
        exact_match : bool, optional
            Whether to match the name(s) exactly. Default is True.
        created_by : str, optional
            Filter teams by the user ID of their creator.
        updated_by : str, optional
            Filter teams by the user ID of their last updater.
        user_id : str or list[str], optional
            Filter teams by user membership.
        max_items : int, optional
            Maximum total number of items to return. If None, fetches all available items.

        Returns
        -------
        Iterator[Team]
            An iterator of Team entities matching the filters.
        """
        params: dict = {}
        if name is not None:
            params["name"] = ensure_list(name)
            params["exactMatch"] = exact_match
        if created_by is not None:
            params["createdBy"] = created_by
        if updated_by is not None:
            params["updatedBy"] = updated_by
        if user_id is not None:
            params["userId"] = ensure_list(user_id)

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Team(**item) for item in items],
        )

    @validate_call
    def get_by_id(self, *, id: TeamId) -> Team:
        """Retrieve a team by its ID.

        Parameters
        ----------
        id : TeamId
            The ID of the team.

        Returns
        -------
        Team
            The Team entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Team(**response.json())

    @validate_call
    def create(
        self,
        *,
        name: str,
        members: list[TeamMember] | None = None,
    ) -> Team:
        """Create a new team, optionally with initial members.

        Parameters
        ----------
        name : str
            The name of the team.
        members : list[TeamMember], optional
            Members to add to the team on creation, each with an ID and role.

        Returns
        -------
        Team
            The created Team.
        """
        payload: dict = {"name": name}
        if members:
            acl_entries = [{"id": m.id, "fgc": m.role or "TeamViewer"} for m in members]
            payload["ACL"] = acl_entries

        response = self.session.post(self.base_path, json=payload)
        return Team(**response.json())

    @validate_call
    def update(self, *, team: Team) -> Team:
        """Update a team's name and membership.

        Parameters
        ----------
        team : Team
            The team with desired changes applied. Modify the ``name``,
            add or remove entries from ``members``, or change a member's
            ``role`` before calling this method.

        Returns
        -------
        Team
            The updated Team.
        """
        current = self.get_by_id(id=team.id)
        url = f"{self.base_path}/{team.id}"
        operations = []

        # Name diff
        if current.name != team.name:
            operations.append(
                {
                    "operation": "update",
                    "attribute": "name",
                    "oldValue": current.name,
                    "newValue": team.name,
                }
            )

        # Member diff — None means "no change", empty list means "remove all"
        if team.members is not None:
            current_ids = {m.id for m in current.members or []}
            updated_ids = {m.id for m in team.members}

            added = updated_ids - current_ids
            removed = current_ids - updated_ids

            updated_members = {m.id: m for m in team.members}

            for uid in added:
                member = updated_members[uid]
                role = member.role or "TeamViewer"
                operations.append(
                    {
                        "operation": "add",
                        "attribute": "ACL",
                        "newValue": [{"id": uid, "fgc": role}],
                    }
                )

            for uid in removed:
                operations.append(
                    {
                        "operation": "delete",
                        "attribute": "ACL",
                        "oldValue": [{"id": uid}],
                    }
                )

            # Role changes for existing members
            current_members = {m.id: m for m in current.members or []}
            for uid in current_ids & updated_ids:
                updated_role = updated_members[uid].role
                current_role = current_members[uid].role
                if current_role is None or updated_role is None:
                    continue
                if updated_role != current_role:
                    operations.append(
                        {
                            "operation": "update",
                            "attribute": "fgc",
                            "oldValue": current_role,
                            "newValue": updated_role,
                            "id": uid,
                        }
                    )

        if operations:
            payload = {"data": operations}
            self.session.patch(url, json=payload)

        return self.get_by_id(id=team.id)

    @validate_call
    def delete(self, *, id: TeamId) -> None:
        """Delete a team by its ID.

        Parameters
        ----------
        id : TeamId
            The ID of the team to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def add_users(
        self,
        *,
        id: TeamId,
        members: list[TeamMember],
    ) -> Team:
        """Add users to a team.

        Parameters
        ----------
        id : TeamId
            The ID of the team.
        members : list[TeamMember]
            The members to add, each with an ID and role.

        Raises
        ------
        AlbertException
            If any of the provided users is already a member. Use ``update``
            to change an existing member's role.

        Returns
        -------
        Team
            The updated Team.
        """
        current = self.get_by_id(id=id)
        existing_ids = {m.id for m in current.members or []}

        new_ids = [m.id for m in members]
        already_present = [uid for uid in new_ids if uid in existing_ids]
        if already_present:
            raise AlbertException(
                f"Users already in team {id}: {already_present}. Use update() to change roles."
            )

        acl_entries = [{"id": m.id, "fgc": m.role or "TeamViewer"} for m in members]
        url = f"{self.base_path}/{id}"
        payload = {
            "data": [
                {
                    "operation": "add",
                    "attribute": "ACL",
                    "newValue": acl_entries,
                }
            ],
        }
        self.session.patch(url, json=payload)
        return self.get_by_id(id=id)

    @validate_call
    def remove_users(
        self,
        *,
        id: TeamId,
        users: list[User | UserId],
    ) -> Team:
        """Remove users from a team.

        Parameters
        ----------
        id : TeamId
            The ID of the team.
        users : list[User | UserId]
            The users to remove. Accepts User objects or user ID strings.

        Raises
        ------
        AlbertException
            If none of the provided users are members of the team.

        Returns
        -------
        Team
            The updated Team.
        """
        current = self.get_by_id(id=id)
        existing_ids = {m.id for m in current.members or []}

        user_ids = [self._resolve_user_id(u) for u in users]
        present = [uid for uid in user_ids if uid in existing_ids]
        if not present:
            raise AlbertException(f"None of the provided users are members of team {id}.")

        acl_entries = [{"id": uid} for uid in present]
        url = f"{self.base_path}/{id}"
        payload = {
            "data": [
                {
                    "operation": "delete",
                    "attribute": "ACL",
                    "oldValue": acl_entries,
                }
            ],
        }
        self.session.patch(url, json=payload)
        return self.get_by_id(id=id)
