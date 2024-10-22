from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.teams import Team
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

    def list(self, *, params: dict | None = None) -> Iterator[Team]:
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
        if params is None:
            params = {}
        response = self.session.get(self.base_path, params=params)
        team_data = response.json().get("Items", [])
        yield from team_data
