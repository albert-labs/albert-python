from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from typing import Any, TypeVar
from urllib.parse import quote_plus

from albert.exceptions import AlbertException
from albert.session import AlbertSession

ItemType = TypeVar("ItemType")


class PaginationMode(str, Enum):
    OFFSET = "offset"
    KEY = "key"


class AlbertPaginator(Iterator[ItemType]):
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
        deserialize: Callable[[Iterable[dict]], Iterable[ItemType]],
        params: dict[str, str] | None = None,
    ):
        self.path = path
        self.mode = mode
        self.session = session
        self.deserialize = deserialize

        params = params or {}
        self.params = {k: v for k, v in params.items() if v is not None}

        if "startKey" in self.params:
            self.params["startKey"] = quote_plus(self.params["startKey"])

        self._iterator = self._create_iterator()

    def _create_iterator(self) -> Iterator[ItemType]:
        while True:
            response = self.session.get(self.path, params=self.params)
            data = response.json()

            items = data.get("Items", [])
            item_count = len(items)

            # Return if no items
            if item_count == 0:
                return

            yield from self.deserialize(items)

            # Return if under limit
            if "limit" in self.params and item_count < self.params["limit"]:
                return

            keep_going = self._update_params(data, item_count)
            if not keep_going:
                return

    def _update_params(self, data: dict[str, Any], count: int) -> bool:
        match self.mode:
            case PaginationMode.OFFSET:
                offset = data.get("offset")
                if not offset:
                    return False
                self.params["offset"] = int(offset) + count
            case PaginationMode.KEY:
                last_key = data.get("lastKey")
                if not last_key:
                    return False
                self.params["startKey"] = quote_plus(last_key)
            case mode:
                raise AlbertException(f"Unknown pagination mode {mode}.")
        return True

    def __iter__(self) -> Iterator[ItemType]:
        return self

    def __next__(self) -> ItemType:
        return next(self._iterator)
