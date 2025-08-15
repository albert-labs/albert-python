from collections.abc import Iterator

import jwt
from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import UserId
from albert.exceptions import AlbertHTTPError
from albert.resources.users import User, UserFilterType, UserSearchItem


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

    @validate_call
    def get_by_id(self, *, id: UserId) -> User:
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

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        sort_by: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        roles: list[str] | None = None,
        teams: list[str] | None = None,
        locations: list[str] | None = None,
        status: list[Status] | None = None,
        user_id: list[UserId] | None = None,
        subscription: list[str] | None = None,
        search_fields: list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        mentions: bool | None = None,
        offset: int = 0,
        max_items: int | None = None,
    ) -> Iterator[UserSearchItem]:
        """
        Searches for users matching the provided filters.

        ⚠️ This method returns partial (unhydrated) search results for performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Free text search across multiple user fields.
        sort_by : str, optional
            Field to sort results by.
        order_by : OrderBy, optional
            Sort order, ascending or descending.
        roles : list[str], optional
            Filter by assigned roles.
        teams : list[str], optional
            Filter by teams.
        locations : list[str], optional
            Filter by associated location IDs.
        status : list[Status], optional
            Filter by user status.
        user_id : list[str], optional
            Filter by specific user IDs.
        subscription : list[str], optional
            Filter by subscription type.
        search_fields : list[str], optional
            Fields to apply text search across.
        facet_text : str, optional
            Text to search within facets.
        facet_field : str, optional
            Facet field to apply facet_text on.
        contains_field : list[str], optional
            Field names for "contains" filter logic.
        contains_text : list[str], optional
            Text snippets to search in "contains" fields.
        mentions : bool, optional
            Filter by users who are mentioned.
        offset : int, optional
            Number of results to skip for pagination. Default is 0.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[UserSearchItem]
            An iterator of partial user results matching the criteria.
        """
        params = {
            "text": text,
            "sortBy": sort_by,
            "order": order_by.value,
            "roles": roles,
            "teams": teams,
            "locations": locations,
            "status": status,
            "userId": user_id,
            "subscription": subscription,
            "searchFields": search_fields,
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": contains_field,
            "containsText": contains_text,
            "mentions": mentions,
            "offset": offset,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                UserSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    @validate_call
    def get_all(
        self,
        *,
        status: Status | None = None,
        type: UserFilterType | None = None,
        id: list[UserId] | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[User]:
        """
        Retrieve fully hydrated User entities with optional filters.

        This method uses `get_by_id` to hydrate the results for convenience.
        Use :meth:`search` for better performance.

        Parameters
        ----------
        status : Status, optional
            Filter by user status.
        type : UserFilterType, optional
            Attribute name to filter by (e.g., 'role').
        id : list[str], optional
            Values of the attribute to filter on.
        start_key : str, optional
            The starting point for the next set of results.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[User]
            User entities.
        """
        params = {
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
            max_items=max_items,
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
