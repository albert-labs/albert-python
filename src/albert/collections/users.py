import logging
from collections.abc import Iterator

import jwt

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.models.enums import Status
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.exceptions import AlbertHTTPError
from albert.resources.users import User, UserFilterParams, UserFilterType, UserSearchItem


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

    def search(self, *, params: UserFilterParams | None = None) -> Iterator[User]:
        """
        Searches for Users matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) search results for performance.
        To retrieve fully detailed objects, use :meth:`get_all` instead.

        Parameters
        ----------
        params : UserFilterParams, optional
            Structured search filters for user listing.

        Returns
        -------
        Iterator[User]
            An iterator of partial User entities.
        """

        params = params or UserFilterParams()
        query_params = params.model_dump(exclude_none=True, by_alias=True)

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=query_params,
            deserialize=lambda items: [UserSearchItem(**item) for item in items],
        )

    def get_all(
        self,
        *,
        limit: int = 100,
        status: Status | None = None,
        type: UserFilterType | None = None,
        id: list[str] | None = None,
        start_key: str | None = None,
    ) -> Iterator[User]:
        """
        Retrieve fully hydrated User entities with optional filters.

        This method uses `get_by_id` to hydrate the results for convenience.
        Use :meth:`search` for better performance.

        Parameters
        ----------
        limit : int
            Max results per page.
        status : Status, optional
            Filter by user status.
        type : UserFilterType
            Attribute name to filter by (e.g., 'role').
        id : list[str], optional
            Values of the attribute to filter on.
        start_key : Optional[str], optional
            The starting point for the next set of results, by default None.

        Returns
        -------
        Iterator[User]
            Fully hydrated User entities.
        """
        params = {
            "limit": limit,
            "status": status,
            "type": type.value if type else None,
            "id": id,
            "startKey": start_key,
        }

        def deserialize(items: list[dict]) -> Iterator[User]:
            for item in items:
                user_id = item.get("albertId")
                if user_id:
                    try:
                        yield self.get_by_id(id=user_id)
                    except AlbertHTTPError as e:
                        logger.warning(f"Error fetching user '{user_id}': {e}")

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
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

        hits = self.search(UserFilterParams(text=user.email))
        for u in hits:
            if u.email == user.email:
                logging.warning(
                    f"User with email {user.email} already exists. Returning existing user."
                )
                return u

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
