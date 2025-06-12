import urllib

from albert.collections.base import BaseCollection
from albert.resources.roles import Role
from albert.session import AlbertSession


class RoleCollection(BaseCollection):
    """RoleCollection is a collection class for managing Role entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the RoleCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{RoleCollection._api_version}/acl/roles"

    def get_by_id(self, *, id: str) -> Role:
        """
        Retrieve a Role by its ID.
        Parameters
        ----------
        id : str
            The ID of the role.
        Returns
        -------
        Role
            The retrieved role.
        """
        # role IDs have # symbols
        url = urllib.parse.quote(f"{self.base_path}/{id}")
        response = self.session.get(url=url)
        return Role(**response.json())

    def create(self, *, role: Role):
        """
        Create a new role.
        Parameters
        ----------
        role : Role
            The role to create.
        """
        response = self.session.post(
            self.base_path,
            json=role.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Role(**response.json())

    def list(self, *, params: dict | None = None) -> list[Role]:
        """Lists the available Roles

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
        role_data = response.json().get("Items", [])
        return [Role(**r) for r in role_data]
