from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.users import UserCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.personalization import Personalization, PersonalizationCategory

# The list endpoint parses `limit` with no fallback, so the SDK always sends a page size.
_PERSONALIZATION_PAGE_LIMIT = 200


class PersonalizationCollection(BaseCollection):
    """Manage user personalization records in the Albert platform.

    Personalization records store per-user preferences such as starred projects,
    hidden rows, and saved filters. Records always belong to a user: records
    created or listed without an explicit user belong to the current user.

    This collection is accessed as ``client.personalization``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.personalization import Personalization, PersonalizationCategory

        client = Albert()
        record = client.personalization.create(
            personalization=Personalization(
                category=PersonalizationCategory.STARRED_PROJECTS,
                saved_id="PRO123",
                saved_name="Weatherproof Coatings 2026",
            )
        )
        print(record.id)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for personalization requests.

    Methods
    -------
    create(personalization) -> Personalization
        Create a new personalization record for the current user.
    get_by_id(id) -> Personalization
        Get a single personalization record by its ID.
    get_all(...) -> Iterator[Personalization]
        Get personalization records, with optional filters.
    delete(id) -> None
        Delete a personalization record by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{PersonalizationCollection._api_version}/personalization"

    @validate_call
    def create(self, *, personalization: Personalization) -> Personalization:
        """Create a new personalization record for the current user.

        !!! example
            ```python
            from albert.resources.personalization import Personalization, PersonalizationCategory

            record = client.personalization.create(
                personalization=Personalization(
                    category=PersonalizationCategory.STARRED_PROJECTS,
                    saved_id="PRO123",
                    saved_name="Weatherproof Coatings 2026",
                )
            )
            record.id
            # 'USP123'
            ```

        Parameters
        ----------
        personalization : Personalization
            The record to create. Requires ``category`` plus the fields the
            category stores (e.g. ``saved_id`` and ``saved_name`` for a starred
            project).

        Returns
        -------
        Personalization
            The created record, populated with its assigned ID.
        """
        payload = personalization.model_dump(
            by_alias=True, exclude_none=True, exclude_unset=True, mode="json"
        )
        response = self.session.post(self.base_path, json=[payload])
        return Personalization(**response.json()[0])

    @validate_call
    def get_by_id(self, *, id: str) -> Personalization:
        """Get a personalization record by its ID.

        !!! example
            ```python
            record = client.personalization.get_by_id(id="USP123")
            record.category
            # <PersonalizationCategory.STARRED_PROJECTS: 'Starred Projects'>
            ```

        Parameters
        ----------
        id : str
            The ID of the record to retrieve (format ``USP...``).

        Returns
        -------
        Personalization
            The fully populated record.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Personalization(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        category: PersonalizationCategory | None = None,
        sub_category: str | None = None,
        saved_id: str | None = None,
        user_id: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Personalization]:
        """Get personalization records, with optional filters.

        Records are listed either for one user or for one saved entity across
        users: pass ``saved_id`` for the latter. When neither ``saved_id`` nor
        ``user_id`` is given, records of the current user are returned.

        !!! example
            ```python
            from albert.resources.personalization import PersonalizationCategory

            for record in client.personalization.get_all(
                category=PersonalizationCategory.STARRED_PROJECTS
            ):
                print(record.id, record.saved_id)
            ```

        Parameters
        ----------
        category : PersonalizationCategory, optional
            Only return records in this category.
        sub_category : str, optional
            Only return records in this subcategory. Requires ``category``.
        saved_id : str, optional
            Only return records saving this entity ID (e.g. a Project ID),
            across users. Cannot be combined with ``user_id``.
        user_id : str, optional
            Only return records belonging to this user. Cannot be combined with
            ``saved_id``. Defaults to the current user when neither is given.
        max_items : int, optional
            Maximum number of records to return in total. If None, returns all
            matching records.

        Returns
        -------
        Iterator[Personalization]
            An iterator of matching records.

        Raises
        ------
        ValueError
            If both ``saved_id`` and ``user_id`` are given, or ``sub_category``
            is given without ``category``.
        """
        params = self._get_all_params(
            category=category, sub_category=sub_category, saved_id=saved_id, user_id=user_id
        )
        if "savedId" not in params and "createdBy" not in params:
            params["createdBy"] = UserCollection(session=self.session).get_current_user().id
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Personalization(**item) for item in items],
        )

    @validate_call
    def delete(self, *, id: str) -> None:
        """Delete a personalization record by its ID.

        !!! example
            ```python
            client.personalization.delete(id="USP123")
            ```

        Parameters
        ----------
        id : str
            The ID of the record to delete (format ``USP...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @staticmethod
    def _get_all_params(
        *,
        category: PersonalizationCategory | None,
        sub_category: str | None,
        saved_id: str | None,
        user_id: str | None,
    ) -> dict[str, Any]:
        """Build the query parameters for a personalization list request."""
        if saved_id and user_id:
            raise ValueError("Only one of `saved_id` or `user_id` can be provided.")
        if sub_category and not category:
            raise ValueError("`category` is required when `sub_category` is provided.")
        params: dict[str, Any] = {"limit": _PERSONALIZATION_PAGE_LIMIT}
        if saved_id:
            params["savedId"] = saved_id
        elif user_id:
            params["createdBy"] = user_id
        if category:
            params["category"] = category.value
        if sub_category:
            params["subCategory"] = sub_category
        return params
