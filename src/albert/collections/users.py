from collections.abc import Iterator

import jwt

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.base import Status
from albert.resources.users import User
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


class UserCollection(BaseCollection):
    """UserCollection is a collection class for managing User entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "status", "email", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the UserCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UserCollection._api_version}/users"

    def get_current_user(self) -> User:
        """
        Retrieves the current authenticated user.

        Returns
        -------
        User
            The current User object.
        """
        claims = jwt.decode(self.session._access_token, options={"verify_signature": False})
        return self.get_by_id(id=claims["id"])

    def get_by_id(self, *, id: str) -> User:
        """
        Retrieves a User by its ID.

        Parameters
        ----------
        id : str
            The ID of the user to retrieve.

        Returns
        -------
        User
            The User object.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return User(**response.json())

    def list(
        self,
        *,
        limit: int = 50,
        offset: int | None = None,
        text: str | None = None,
        status: Status | None = None,
        search_fields: str | None = None,
    ) -> Iterator[User]:
        """Lists Users based on criteria

        Parameters
        ----------
        text : Optional[str], optional
            text to search against, by default None

        Returns
        -------
        Generator
            Generator of matching Users or None
        """

        def deserialize(items: list[dict]) -> Iterator[User]:
            for item in items:
                id = item["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching user '{id}': {e}")

        params = {
            "limit": limit,
            "offset": offset,
            "status": status,
            "text": text,
            "searchFields": search_fields,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=deserialize,
        )

    def create(self, *, user: User) -> User:  # pragma: no cover
        """Create a new User

        Parameters
        ----------
        user : User
            The user to create

        Returns
        -------
        User
            The created User
        """

        response = self.session.post(
            self.base_path,
            json=user.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return User(**response.json())

    def update(self, *, user: User) -> User:
        """Update a User entity.

        Parameters
        ----------
        user : User
            The updated User entity.

        Returns
        -------
        User
            The updated User entity as returned by the server.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=user.id)

        # Generate the PATCH payload
        payload = self._generate_patch_payload(existing=current_object, updated=user)

        url = f"{self.base_path}/{user.id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))

        updated_user = self.get_by_id(id=user.id)
        return updated_user
