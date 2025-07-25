import json
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.exceptions import AlbertException

ItemType = TypeVar("ItemType")
DEFAULT_LIMIT = 1000


class AlbertPaginator(Iterator[ItemType]):
    """Helper class for pagination through Albert endpoints.

    - Offset-based pagination (`PaginationMode.OFFSET`)
        - Uses the `offset` query parameter in the request
        - Continues until the response contains no `Items` (i.e., an empty list)
        - The `limit` parameter is set to 1000 by default (applies to most search functions)

    - Key-based pagination (`PaginationMode.KEY`)
        - Uses the `startKey` query parameter and expects a `lastKey` in the response
        - Continues until `lastKey` is not present in the response
        - The page size limit is not explicitly set in the query; it defaults to what the backend API provides

    A custom `deserialize` function is provided when additional logic is required to load
    the raw items returned by the search listing, e.g., making additional Albert API calls.
    The `max_items` argument can be used to stop iteration early, regardless of mode.
    """

    def __init__(
        self,
        *,
        path: str,
        mode: PaginationMode,
        session: AlbertSession,
        deserialize: Callable[[Iterable[dict]], Iterable[ItemType]],
        params: dict[str, str] | None = None,
        max_items: int | None = None,
    ):
        self.path = path
        self.mode = mode
        self.session = session
        self.deserialize = deserialize
        self.max_items = max_items

        params = params or {}
        self.params = self._encode_query_params(params)

        if self.mode == PaginationMode.OFFSET:
            self.params.setdefault("limit", DEFAULT_LIMIT)

        self._last_key: str | None = None

        self._iterator = self._create_iterator()

    def _encode_query_params(self, params: dict) -> dict:
        """Encode and clean up query parameters for the request."""
        return {
            k: json.dumps(v) if isinstance(v, bool) else v
            for k, v in params.items()
            if v is not None
        }

    @property
    def last_key(self) -> str | None:
        """Returns the most recent pagination key ('lastKey') received from the API.

        This key can be used to resume fetching items from the next page, unless pagination
        was stopped early by 'max_items', in which case some items on the last page may not have been iterated.
        Returns None if no key has been received yet."""
        return self._last_key

    def _create_iterator(self) -> Iterator[ItemType]:
        yielded = 0
        while True:
            response = self.session.get(self.path, params=self.params)
            data = response.json()
            items = data.get("Items", [])
            item_count = len(items)

            if not items and self.mode == PaginationMode.OFFSET:
                return

            deserialized = list(self.deserialize(items))

            for item in deserialized:
                yield item
                yielded += 1
                if self.max_items is not None and yielded >= self.max_items:
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
                self._last_key = last_key
                if not last_key:
                    return False
                self.params["startKey"] = last_key
            case mode:
                raise AlbertException(f"Unknown pagination mode {mode}.")
        return True

    def __iter__(self) -> Iterator[ItemType]:
        return self

    def __next__(self) -> ItemType:
        return next(self._iterator)
