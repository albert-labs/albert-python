import urllib

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.roles import Role


class RoleCollection(BaseCollection):
    """Manage Roles in the Albert platform.

    A Role defines a set of access permissions (policies) within a tenant.
    Roles are assigned to users ([`User`][albert.resources.users.User]) to
    govern what they can do, and are referenced by entity ACLs alongside the
    users they apply to.

    This collection is accessed as ``client.roles``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for role requests.

    Methods
    -------
    get_by_id(id) -> Role
        Retrieve a single role by its ID.
    get_all(params=None) -> list[Role]
        Retrieve all available roles.
    create(role) -> Role
        Register a new role.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        roles = client.roles.get_all()
        for role in roles:
            print(role.id, role.name)
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a RoleCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{RoleCollection._api_version}/acl/roles"

    def get_by_id(self, *, id: str) -> Role:
        """Retrieve a single role by its ID.

        Parameters
        ----------
        id : str
            The ID of the role. Role IDs may contain ``#`` characters and are
            URL-encoded automatically.

        Returns
        -------
        Role
            The retrieved role.

        !!! example
            ```python
            role = client.roles.get_by_id(id="role#admin")
            role.name
            # 'Administrator'
            ```
        """
        # role IDs have # symbols
        url = urllib.parse.quote(f"{self.base_path}/{id}")
        response = self.session.get(url=url)
        return Role(**response.json())

    def create(self, *, role: Role):
        """Register a new role.

        Parameters
        ----------
        role : Role
            The role to create.

        Returns
        -------
        Role
            The newly created role.

        !!! example
            ```python
            from albert.resources.roles import Role
            role = client.roles.create(role=Role(name="Lab Analyst", tenant="TEN123"))
            role.id
            ```
        """
        response = self.session.post(
            self.base_path,
            json=role.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Role(**response.json())

    def get_all(self, *, params: dict | None = None) -> list[Role]:
        """Retrieve all available roles.

        Parameters
        ----------
        params : dict, optional
            Optional query parameters passed through to the API to filter or
            shape the results. Defaults to no parameters.

        Returns
        -------
        list[Role]
            All roles available in the tenant.

        !!! example
            ```python
            roles = client.roles.get_all()
            [r.name for r in roles]
            # ['Administrator', 'Standard User']
            ```
        """
        if params is None:
            params = {}
        response = self.session.get(self.base_path, params=params)
        role_data = response.json().get("Items", [])
        return [Role(**r) for r in role_data]
