from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from typing import Any, TypeVar

from albert.session import AlbertSession
from albert.utils.exceptions import AlbertException

ItemType = TypeVar("ItemType")


class PaginationMode(str, Enum):
    OFFSET = "offset"
    KEY = "key"


class AlbertPaginator(Iterable[ItemType]):
    """Helper class for pagination through Albert endpoints.

    Two pagination modes are possible:
        - Offset-based via by the `offset` query parameter
        - Key-based via by the `startKey` query parameter and 'lastKey' response field

    A custom `deserialize` function is provided when additional logic is required to load
    the raw items returned by the search listing, e.g., making additional Albert API calls.
    """

    def __init__(
        self,
        *,
        path: str,
        mode: PaginationMode,
        session: AlbertSession,
        deserialize: Callable[[dict], ItemType | None],
        params: dict[str, str] | None = None,
    ):
        self.path = path
        self.mode = mode
        self.session = session
        self.deserialize = deserialize

        params = params or {}
        self.params = {k: v for k, v in params.items() if v is not None}

    def _update_params(self, data: dict[str, Any], item_count: int) -> bool:
        match self.mode:
            case PaginationMode.OFFSET:
                offset = data.get("offset")
                if not offset:
                    return False
                self.params["offset"] = int(offset) + item_count
            case PaginationMode.KEY:
                last_key = data.get("lastKey")
                if not last_key:
                    return False
                self.params["startKey"] = last_key
            case mode:
                raise AlbertException(f"Unknown pagination mode {mode}.")
        return True

    def __iter__(self) -> Iterator[ItemType]:
        while True:
            response = self.session.get(self.path, params=self.params)
            response_data = response.json()

            items = response_data.get("Items", [])
            item_count = len(items)

            # Return early for insufficient items
            no_items = item_count == 0
            under_limit = "limit" in self.params and item_count < self.params["limit"]
            if no_items or under_limit:
                return

            for item in items:
                item_deser = self.deserialize(item)
                if item_deser is None:
                    continue
                yield item_deser

            keep_going = self._update_params(response_data, item_count)
            if not keep_going:
                return
