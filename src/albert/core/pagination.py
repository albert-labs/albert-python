from collections.abc import Callable, Iterable, Iterator
from itertools import islice
from typing import Any, TypeVar
from urllib.parse import quote_plus

from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.exceptions import AlbertException

ItemType = TypeVar("ItemType")


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
        page_size: int = 100,
        max_items: int | None = None,
    ):
        self.path = path
        self.mode = mode
        self.session = session
        self.deserialize = deserialize
        self.page_size = page_size
        self.max_items = max_items

        params = params or {}
        self.params = {k: v for k, v in params.items() if v is not None}

        if "startKey" in self.params:
            self.params["startKey"] = quote_plus(self.params["startKey"])
        self.params["limit"] = self.page_size

        self._iterator = self._create_iterator()

    def _create_iterator(self) -> Iterator[ItemType]:
        while True:
            response = self.session.get(self.path, params=self.params)
            data = response.json()
            items = data.get("Items", [])
            item_count = len(items)
            if not items:
                return

            yield from self.deserialize(items)

            if item_count < self.page_size:
                return

            if not self._update_params(data=data, count=item_count):
                return

    def _update_params(self, *, data: dict[str, Any], count: int) -> bool:
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
        return (
            islice(self._iterator, self.max_items)
            if self.max_items is not None
            else self._iterator
        )

    def __next__(self) -> ItemType:
        return next(self._iterator)
