from collections.abc import Iterator

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
    """Manage Users in the Albert platform.

    A User is an Albert user account: a person who can log in and act in the
    platform. Each user has a name and email, a set of
    :class:`~albert.resources.roles.Role` objects that govern what they can do,
    an optional home :class:`~albert.resources.locations.Location`, and an ACL
    class level (:class:`~albert.resources.users.UserClass`) that sets a broad
    permission tier.

    Users are grouped into teams (see
    :class:`~albert.collections.teams.TeamCollection`), and are referenced
    throughout the platform: Tasks can be assigned to a user, and entities carry
    ACLs that reference users and their roles. A user is identified by its User
    ID (format ``USR...``, e.g. ``"USR12"``).

    This collection is accessed as ``client.users``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for user requests.

    Methods
    -------
    get_current_user() -> User
        Retrieve the user account for the currently authenticated session.
    get_by_id(id) -> User
        Retrieve a single fully populated user by its User ID.
    search(...) -> Iterator[UserSearchItem]
        Fast, lightweight search returning partial users (best for lookups).
    get_all(...) -> Iterator[User]
        Same idea as search, but returns fully populated users (slower).
    create(user) -> User
        Register a new user account.
    update(user) -> User
        Apply changes to an existing user.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        # Look up the signed-in user, then find others at the same location
        me = client.users.get_current_user()
        colleagues = client.users.get_all(max_items=25)
        for user in colleagues:
            print(user.id, user.name, user.email)
        ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "status", "email", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a UserCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UserCollection._api_version}/users"

    def get_current_user(self) -> User:
        """Retrieve the user account for the currently authenticated session.

        Use this to find out who the active credentials belong to, for example
        to set yourself as the assignee of a Task or to check your own roles.

        Returns
        -------
        User
            The fully populated user for the authenticated session.

        Examples
        --------
        !!! example
            ```python
            me = client.users.get_current_user()
            me.name
            # 'Ada Lovelace'
            ```
        """
        response = self.session.get(
            "/api/v3/login/validatejwt",
            params={"includeUserDetails": True},
        )
        payload = response.json()
        user_id = payload.get("userId")
        if not user_id:
            raise ValueError("Current user lookup failed.")
        return self.get_by_id(id=user_id)

    @validate_call
    def get_by_id(self, *, id: UserId) -> User:
        """Retrieve a single, fully populated user by their ID.

        To find users without knowing their IDs, use :meth:`search` or
        :meth:`get_all`.

        Parameters
        ----------
        id : UserId
            The User ID (format ``USR...``, e.g. ``"USR12"``).

        Returns
        -------
        User
            The fully populated user.

        Examples
        --------
        !!! example
            ```python
            user = client.users.get_by_id(id="USR12")
            user.email
            # 'ada@example.com'
            ```
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
        """Search for users matching the provided filters.

        This returns lightweight, partial results (:class:`UserSearchItem`) and
        is the fastest way to look users up by name, role, team, or location.
        For fully populated :class:`User` entities, use :meth:`get_all`, or call
        :meth:`~albert.resources._mixins.HydrationMixin.hydrate` on a search item.

        Parameters
        ----------
        text : str, optional
            Free-text search across multiple user fields (e.g. name, email).
        sort_by : str, optional
            Field to sort results by.
        order_by : OrderBy, optional
            Sort direction, ascending or descending. Defaults to descending.
        roles : list[str], optional
            Restrict to users holding any of these role names.
        teams : list[str], optional
            Restrict to members of any of these teams.
        locations : list[str], optional
            Restrict to users at any of these location IDs.
        status : list[Status], optional
            Restrict to users with any of these statuses (e.g. active, inactive).
        user_id : list[UserId], optional
            Restrict to these specific User IDs.
        subscription : list[str], optional
            Restrict to users with any of these subscription types.
        search_fields : list[str], optional
            The fields that ``text`` is matched against.
        facet_text : str, optional
            Text to match within a facet, used together with ``facet_field``.
        facet_field : str, optional
            The facet field that ``facet_text`` is applied to.
        contains_field : list[str], optional
            Field names to apply "contains" filtering on, paired positionally
            with ``contains_text``.
        contains_text : list[str], optional
            Substrings to match within the corresponding ``contains_field``.
        mentions : bool, optional
            When True, restrict to users who are mentioned.
        max_items : int, optional
            Maximum total number of users to return. If None, returns all
            matches.

        Returns
        -------
        Iterator[UserSearchItem]
            An iterator of partial users matching the filters.

        Examples
        --------
        !!! example
            ```python
            # Find users whose name or email mentions "ada"
            for user in client.users.search(text="ada", max_items=10):
                print(user.id, user.name)
            ```
        """
        params = {
            "text": text,
            "sortBy": sort_by,
            "order": order_by,
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
        """Retrieve fully populated users, with optional filters.

        Each result is fetched individually via :meth:`get_by_id`, so this is
        convenient but slower than :meth:`search`. Prefer :meth:`search` when
        you only need lightweight, partial results.

        Parameters
        ----------
        status : Status, optional
            Restrict to users with this status (e.g. active, inactive).
        type : UserFilterType, optional
            The attribute that ``id`` filters on. Currently only ``role`` is
            supported.
        id : list[UserId], optional
            The values to filter on for the chosen ``type`` (e.g. role IDs when
            ``type`` is ``role``).
        start_key : str, optional
            Pagination cursor marking where the next page of results begins.
        max_items : int, optional
            Maximum total number of users to return. If None, returns all
            matches.

        Returns
        -------
        Iterator[User]
            An iterator of fully populated users.

        Examples
        --------
        !!! example
            ```python
            from albert.core.shared.enums import Status
            active_users = client.users.get_all(status=Status.ACTIVE, max_items=50)
            for user in active_users:
                print(user.name)
            ```
        """
        params = {
            "status": status,
            "type": type,
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
        """Register a new user account.

        Parameters
        ----------
        user : User
            The user to create. ``name`` is required; set ``email``, ``roles``,
            ``location``, and ``user_class`` as needed.

        Returns
        -------
        User
            The newly created user, populated with its assigned User ID.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.users import User, UserClass
            new_user = User(
                name="Ada Lovelace",
                email="ada@example.com",
                user_class=UserClass.STANDARD,
            )
            created = client.users.create(user=new_user)
            created.id
            # 'USR12'
            ```
        """

        response = self.session.post(
            self.base_path,
            json=user.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return User(**response.json())

    def update(self, *, user: User) -> User:
        """Apply changes to an existing user.

        Fetch the user (e.g. via :meth:`get_by_id`), modify the updatable
        fields, then pass it here. Only the difference against the current
        server state is sent.

        Parameters
        ----------
        user : User
            The user with desired changes applied. Must carry a valid ``id``.

        Returns
        -------
        User
            The updated user as returned by the server.

        Notes
        -----
        The following fields can be updated: ``email``, ``metadata``, ``name``,
        ``status``.

        Examples
        --------
        !!! example
            ```python
            user = client.users.get_by_id(id="USR12")
            user.name = "Ada King"
            updated = client.users.update(user=user)
            updated.name
            # 'Ada King'
            ```
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=user.id)

        # Generate the PATCH payload
        payload = self._generate_patch_payload(existing=current_object, updated=user)

        url = f"{self.base_path}/{user.id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))

        updated_user = self.get_by_id(id=user.id)
        return updated_user
