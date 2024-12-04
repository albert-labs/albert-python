import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.un_numbers import UnNumber
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class UnNumberCollection(BaseCollection):
    """
    UnNumberCollection is a collection class for managing UN Numbers.

    Note
    ----
    Creating UN Numbers is not supported via the SDK, as UN Numbers are highly controlled by Albert.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{UnNumberCollection._api_version}/unnumbers"

    def create(self) -> None:
        """
        This method is not implemented as UN Numbers cannot be created through the SDK.
        """
        raise NotImplementedError()

    def get_by_id(self, *, id: str) -> UnNumber:
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return UnNumber(**response.json())

    def get_by_name(self, *, name: str) -> UnNumber | None:
        found = self.list(exact_match=True, name=name)
        return next(found, None)

    def list(
        self,
        *,
        limit: int = 50,
        start_key: str | None = None,
        name: str | None = None,
        exact_match: bool = False,
    ) -> Iterator[UnNumber, None, None]:
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
