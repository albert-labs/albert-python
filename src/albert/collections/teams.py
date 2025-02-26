from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.acls import ACL
from albert.resources.teams import Team, TeamRole
from albert.resources.users import User
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


class TeamsCollection(BaseCollection):
    """TeamsCollection is a collection class for managing teams entities."""

    _api_version = "v3"
    _updatable_attributes = {"acl"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{TeamsCollection._api_version}/teams"

    def add_users(
        self,
        *,
        team_id: str,
        user_ids: list[str],
        role: TeamRole = TeamRole.TEAM_VIEWER,
    ) -> Team:
        team = self.get_by_id(id=team_id)
        team.acl.extend([ACL(id=id, fgc=role) for id in user_ids])
        return self.update(team=team)

    def remove_users(self, *, team: Team, users: list[User]) -> Team:
        pass

    def get_by_id(self, *, id: str) -> Team:
        """
        Get a team by its ID.

        Parameters
        ----------
        id : str
            The ID of the team to retrieve.

        Returns
        -------
        Team
            The team object.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Team(**response.json())

    def create(self, *, team: Team) -> Team:
        """ """
        response = self.session.post(
            self.base_path, json=team.model_dump(by_alias=True, exclude_none=True)
        )
        return Team(**response.json())

    def update(self, *, team: Team) -> Team:
        existing = self.get_by_id(id=team.id)
        payload = self._generate_patch_payload(
            existing=existing,
            updated=team,
            stringify_values=True,
        )

        path = f"{self.base_path}/{team.id}"
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=team.id)

    def delete(self, *, id: str) -> None:
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def list(
        self,
        *,
        limit: int = 100,
        start_key: str | None = None,
        names: str | list[str] | None = None,
    ) -> Iterator[Team]:
        """Lists the available Teams

        Returns
        -------
        Iterator[Team]
            Iterator of Team resources.
        """

        def deserialize(items: list[dict]) -> Iterator[Team]:
            for item in items:
                id = item["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching custom template {id}: {e}")

        params = {
            "limit": limit,
            "name": names if isinstance(names, str) else names,
            "startKey": start_key,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=deserialize,
        )
