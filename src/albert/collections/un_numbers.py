from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.un_numbers import UnNumber


class UnNumberCollection(BaseCollection):
    """UnNumberCollection is a collection class for managing UnNumber entities in the Albert platform.

    Note
    ----
    Creating UN Numbers is not supported via the SDK, as UN Numbers are highly controlled by Albert.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initializes the UnNumberCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnNumberCollection._api_version}/unnumbers"

    def create(self) -> None:
        """
        This method is not implemented as UN Numbers cannot be created through the SDK.
        """
        raise NotImplementedError()

    def get_by_id(self, *, id: str) -> UnNumber:
        """Retrieve a UN Number by its ID.

        Parameters
        ----------
        id : str
            The ID of the UN Number to retrieve.

        Returns
        -------
        UnNumber
            The corresponding UN Number
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return UnNumber(**response.json())

    def get_by_name(self, *, name: str) -> UnNumber | None:
        """Retrieve a UN Number by its name.

        Parameters
        ----------
        name : str
            The name of the UN Number to retrieve

        Returns
        -------
        UnNumber | None
            The corresponding UN Number or None if not found
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
        """Get all UN Numbers matching the provided criteria.

        Parameters
        ----------
        name : str | None, optional
            The name of the UN Number to search for, by default None.
        exact_match : bool, optional
            Whether to return exact matches only, by default False.
        start_key : str | None, optional
            The pagination key to continue fetching items from, by default None.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

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
