from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

from albert.session import AlbertSession

ItemType = TypeVar("ItemType")


class SearchPaginator(Iterable[ItemType]):
    """Helper class for paginating through Albert 'search' endpoints.

    The search endpoints use a limit/offset pagination scheme which can be handled generally.
    A custom 'deserialize' function is provided when additional logic is required to load
    the raw items returned by the search listing, e.g., making additional Albert API calls.
    """

    def __init__(
        self,
        *,
        path: str,
        session: AlbertSession,
        deserialize: Callable[[dict], ItemType | None],
        params: dict[str, str] | None = None,
    ):
        self.path = path
        self.session = session
        self.deserialize = deserialize
        self.params = {k: v for k, v in params.items() if v is not None}

    def __iter__(self) -> Iterator[ItemType]:
        while True:
            response = self.session.get(self.path, params=self.params)
            response_data = response.json()

            items = response_data.get("Items", [])
            if len(items) == 0:
                return

            for item in items:
                item_deser = self.deserialize(item)
                if item_deser is None:
                    continue
                yield item_deser

            offset = response_data.get("offset")
            if not offset:
                return

            self.params["offset"] = int(offset) + len(items)
