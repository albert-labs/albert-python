from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.un_numbers import UnNumber


class UnNumberCollection(BaseCollection):
    """Look up UN Numbers in the Albert platform.

    A UN Number is the four-digit United Nations identifier assigned to a
    hazardous material for transport (e.g. ``UN1090`` for acetone). In Albert,
    UN Numbers carry the associated shipping and storage-class metadata used when
    classifying substances and inventory items for shipping. Use this collection
    to look them up by ID or name.

    This collection is accessed as ``client.un_numbers``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        un_number = client.un_numbers.get_by_name(name="UN1090")
        un_number.shipping_description
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for UN Number requests.

    Methods
    -------
    get_by_id(id) -> UnNumber
        Get a single UN Number by its ID.
    get_by_name(name) -> UnNumber | None
        Get a UN Number by its exact name, or None if not found.
    get_all(...) -> Iterator[UnNumber]
        Iterate over UN Numbers, optionally filtered by name.
    create() -> None
        Not supported; UN Numbers cannot be created through the SDK.

    Note
    ----
    Creating UN Numbers is not supported via the SDK, as UN Numbers are highly
    controlled by Albert.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a UnNumberCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnNumberCollection._api_version}/unnumbers"

    def create(self) -> None:
        """Not supported; UN Numbers cannot be created through the SDK.

        UN Numbers are highly controlled by Albert and are managed centrally, so
        this method always raises.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            Always, because UN Numbers cannot be created through the SDK.
        """
        raise NotImplementedError()

    def get_by_id(self, *, id: str) -> UnNumber:
        """Get a single UN Number by its ID.

        !!! example
            ```python
            un_number = client.un_numbers.get_by_id(id="...")
            un_number.un_number
            ```

        Parameters
        ----------
        id : str
            The Albert ID of the UN Number to retrieve.

        Returns
        -------
        UnNumber
            The fully populated UN Number.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return UnNumber(**response.json())

    def get_by_name(self, *, name: str) -> UnNumber | None:
        """Get a UN Number by its exact name.

        Runs an exact-match lookup and returns the first result. To browse or
        do partial-name matching, use [`get_all`][albert.collections.un_numbers.UnNumberCollection.get_all].

        !!! example
            ```python
            un_number = client.un_numbers.get_by_name(name="UN1090")
            un_number.storage_class_name if un_number else "not found"
            ```

        Parameters
        ----------
        name : str
            The exact name of the UN Number to retrieve.

        Returns
        -------
        UnNumber | None
            The matching UN Number, or None if no exact match is found.
        """
        found = self.get_all(exact_match=True, name=name)
        return next(found, None)

    def get_all(
        self,
        *,
        name: str | None = None,
        exact_match: bool = False,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[UnNumber]:
        """Iterate over UN Numbers, optionally filtered by name.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand. With no ``name``, iterates over all UN Numbers.

        !!! example
            ```python
            for un_number in client.un_numbers.get_all(name="acetone", max_items=10):
                print(un_number.un_number, un_number.shipping_description)
            ```

        Parameters
        ----------
        name : str, optional
            Filter to UN Numbers whose name matches. Combine with ``exact_match``
            to control whether matching is exact or partial.
        exact_match : bool, optional
            When True, return only exact name matches. Default False.
        start_key : str, optional
            Pagination key of the first record to evaluate; used to resume paging.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Yields
        ------
        Iterator[UnNumber]
            The UN Numbers matching the search criteria.
        """
        params = {"startKey": start_key}
        if name:
            params["name"] = name
            params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [UnNumber(**item) for item in items],
        )
