import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.un_numbers import UnNumber
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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
        found = self.list(exact_match=True, name=name)
        return next(found, None)

    def list(
        self,
        *,
        name: str | None = None,
        exact_match: bool = False,
        limit: int = 50,
        start_key: str | None = None,
    ) -> Iterator[UnNumber]:
        """List UN Numbers matching the provided criteria.

        Parameters
        ----------
        name : str | None, optional
            The name of the UN Number to search for, by default None
        exact_match : bool, optional
            Weather to return exact matches only, by default False

        Yields
        ------
        Iterator[UnNumber]
            The UN Numbers matching the search criteria
        """
        params = {"limit": limit, "startKey": start_key}
        if name:
            params["name"] = name
            params["exactMatch"] = json.dumps(exact_match)
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [UnNumber(**item) for item in items],
        )
