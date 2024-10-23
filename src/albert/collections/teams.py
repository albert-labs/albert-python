from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection
from albert.resources.teams import Team, TeamRole
from albert.resources.users import User
from albert.session import AlbertSession


class TeamsCollection(BaseCollection):
    """
    TeamsCollection is a collection class for managing teams entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for project API requests.

    Methods
    -------
    list(params: dict) -> Iterator
        Lists teams with optional filters.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initialize a TeamsCollection object.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TeamsCollection._api_version}/teams"

    def add_users_to_team(
        self, *, team: Team, users: list[User], team_role: TeamRole = TeamRole.TEAM_VIEWER
    ) -> bool:
        """
        add users to a team
        """
        # build payload
        newValue = []
        for _u in users:
            newValue.append({"id": _u.id, "fgc": team_role})
        payload = [
            {
                "id": team.id,
                "data": [{"operation": "add", "attribute": "ACL", "newValue": newValue}],
            }
        ]
        # run request
        self.session.patch(self.base_path, json=payload)
        return True

    def _list_generator(
        self,
        *,
        limit: int = 100,
        # order_by: OrderBy = OrderBy.DESCENDING,
        name: list[str] = None,
        # exact_match: bool = True,
        # start_key: str | None = None,
    ) -> Generator[Team, None, None]:
        """
        Lists team entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of teams to return, by default 100.

        Returns
        -------
        Generator
            A generator of Team objects.
        """
        params = {"limit": limit}  # , "orderBy": order_by.value}
        if name:
            params["name"] = name if isinstance(name, list) else [name]
        #     params["exactMatch"] = str(exact_match).lower()
        # if start_key:  # pragma: no cover
        #     params["startKey"] = start_key

        while True:
            response = self.session.get(self.base_path, params=params)
            teams_data = response.json().get("Items", [])
            if not teams_data or teams_data == []:
                break
            for t in teams_data:
                this_team = Team(**t)
                yield this_team
            start_key = response.json().get("lastKey")
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self,
        # *,
        # order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] = None,
        # exact_match: bool = True
    ) -> Iterator[Team]:
        """Lists the available Teams

        Parameters
        ----------
        params : dict, optional
            _description_, by default {}

        Returns
        -------
        List
            List of available Roles
        """
        return self._list_generator(name=name)

    def create(self, *, team: Team) -> Team:
        """ """
        response = self.session.post(
            self.base_path, json=team.model_dump(by_alias=True, exclude_none=True)
        )
        return Team(**response.json())

    def delete(self, *, team_id: str) -> bool:
        """ """
        url = f"{self.base_path}/{team_id}"
        self.session.delete(url)
        return True
