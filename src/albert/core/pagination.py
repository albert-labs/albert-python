from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from typing import Any, Literal, TypeVar

from albert.core.async_session import AsyncAlbertSession
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.exceptions import AlbertException

ItemType = TypeVar("ItemType")
OutType = TypeVar("OutType")
DEFAULT_LIMIT = 1000


class AlbertPaginator(Iterator[ItemType]):
    """Helper class for pagination through Albert endpoints.

    - Offset-based pagination (`PaginationMode.OFFSET`)
        - Uses the `offset` parameter in the request
        - Continues until the response contains no `Items` (i.e., an empty list)
        - The `limit` parameter is set to 1000 by default (applies to most search functions)

    - Key-based pagination (`PaginationMode.KEY`)
        - Uses the `startKey` query parameter and expects a `lastKey` in the response
        - Continues until `lastKey` is not present in the response
        - The page size limit is not explicitly set in the query; it defaults to what the backend API provides

    A custom `deserialize` function is provided when additional logic is required to load
    the raw items returned by the search listing, e.g., making additional Albert API calls.
    The `max_items` argument can be used to stop iteration early, regardless of mode.

    After iteration, [`has_more`][albert.core.pagination.AlbertPaginator.has_more] is True
    when the iterator stopped because ``max_items`` was reached and at least one further
    item is known to exist (remaining items on the current page, or a continuation key /
    offset for another page). When iteration runs to natural completion, ``has_more`` is
    False.
    """

    def __init__(
        self,
        *,
        path: str,
        mode: PaginationMode,
        session: AlbertSession,
        deserialize: Callable[[Iterable[dict]], Iterable[ItemType]],
        params: dict[str, str] | None = None,
        method: Literal["GET", "POST"] = "GET",
        json: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        """
        Initialize a paginator for Albert endpoints.

        Parameters
        ----------
        path : str
            Endpoint path to request.
        mode : PaginationMode
            Pagination mode to apply.
        session : AlbertSession
            Session used to perform requests.
        deserialize : Callable[[Iterable[dict]], Iterable[ItemType]]
            Function to convert response items into objects.
        params : dict[str, str] | None, optional
            Query parameters for the request.
        method : Literal["GET", "POST"], optional
            HTTP method to use (default is GET).
        json : dict[str, Any] | None, optional
            JSON body for POST requests.
        max_items : int | None, optional
            Maximum number of items to yield.
        """
        self.path = path
        self.mode = mode
        self.session = session
        self.deserialize = deserialize
        self.max_items = max_items
        self.method = method.upper()
        self.params = params or {}
        self.json = json or {}
        self._pagination_params = self.params if self.method == "GET" else self.json

        if self.mode == PaginationMode.OFFSET:
            self._pagination_params.setdefault("limit", DEFAULT_LIMIT)

        self._last_key: str | None = None
        self._has_more = False
        self._total: int | None = None

        self._iterator = self._create_iterator()

    @property
    def last_key(self) -> str | None:
        """Returns the most recent pagination key ('lastKey') received from the API.

        This key can be used to resume fetching items from the next page, unless pagination
        was stopped early by 'max_items', in which case some items on the last page may not have been iterated.
        Returns None if no key has been received yet."""
        return self._last_key

    @property
    def has_more(self) -> bool:
        """True when iteration stopped early and more matching items are known to exist.

        Set when ``max_items`` cut off the iterator while unyielded items remained on the
        current page, or while the response indicated another page (``lastKey`` / offset
        continuation), or when the response ``total`` exceeds items yielded (backends that
        ignore ``limit`` and return empty for ``offset>0``). False after a natural end of
        results.
        """
        return self._has_more

    @property
    def total(self) -> int | None:
        """Server-reported match count from the latest response, when present."""
        return self._total

    def _record_total(self, data: dict[str, Any]) -> None:
        raw = data.get("total")
        if raw is None:
            return
        try:
            self._total = int(raw)
        except (TypeError, ValueError):
            return

    def _total_implies_more(self, yielded: int) -> bool:
        return self._total is not None and yielded < self._total

    def _create_iterator(self) -> Iterator[ItemType]:
        """Create an iterator that yields paginated items."""
        yielded = 0
        seen_keys: set[str] = set()

        while True:
            response = self._request()
            data = response.json()
            self._record_total(data)
            items = data.get("Items", [])
            item_count = len(items)

            if not items and self.mode == PaginationMode.OFFSET:
                # Backend returned empty for offset>0 while ``total`` still exceeds what
                # we have (common when ``limit`` is ignored and offset is broken).
                if self._total_implies_more(yielded):
                    self._has_more = True
                return

            # Detect repeated keys before yielding to avoid duplicates.
            # Some backends always return lastKey even on the final page.
            # TODO: remove when pagination is fixed in the backend.
            # https://linear.app/albert-invent/issue/TAS-564/inconsistent-cas-pagination-behaviour
            current_key = data.get("lastKey")
            if self.mode == PaginationMode.KEY and current_key is not None:
                if current_key in seen_keys:
                    return
                seen_keys.add(current_key)

            deserialized = list(self.deserialize(items))

            for item in deserialized:
                if self.max_items is not None and yielded >= self.max_items:
                    # Unyielded item on this page — definitive signal more exist.
                    self._has_more = True
                    return
                yield item
                yielded += 1

            if self.max_items is not None and yielded >= self.max_items:
                # Server-reported total is authoritative over a full-page heuristic.
                if self._total is not None:
                    self._has_more = self._total_implies_more(yielded)
                else:
                    self._has_more = self._response_has_continuation(
                        data=data, count=item_count, current_key=current_key
                    )
                return

            if self.mode == PaginationMode.KEY and current_key is None:
                return
            if not self._update_params(data=data, count=item_count):
                if self._total_implies_more(yielded):
                    self._has_more = True
                return

    def _next_request_offset(self, *, data: dict[str, Any], count: int) -> int:
        """Compute the offset for the next page request."""
        offset = data.get("offset")
        if offset is not None:
            return int(offset) + count
        current = self._pagination_params.get("offset", 0)
        return int(current or 0) + count

    def _probe_offset_has_more(self, *, data: dict[str, Any], count: int) -> bool:
        """Return whether another offset page exists (one-item probe)."""
        if count == 0:
            return False
        next_offset = self._next_request_offset(data=data, count=count)
        if self.method == "GET":
            probe_params = {**self.params, "offset": next_offset, "limit": 1}
            response = self.session.get(self.path, params=probe_params)
        else:
            probe_payload = {
                **self.json,
                "offset": next_offset,
                "limit": 1,
            }
            response = self.session.request(
                self.method,
                self.path,
                params=self.params,
                json=self._serialize_payload(probe_payload),
            )
        return bool(response.json().get("Items"))

    def _response_has_continuation(
        self, *, data: dict[str, Any], count: int, current_key: str | None
    ) -> bool:
        """Return whether the current response indicates another page of results."""
        match self.mode:
            case PaginationMode.OFFSET:
                if count == 0:
                    return False
                limit = int(self._pagination_params.get("limit", DEFAULT_LIMIT))
                if count >= limit:
                    return True
                # Short page at max_items cap — backend may page below requested limit.
                return self._probe_offset_has_more(data=data, count=count)
            case PaginationMode.KEY:
                return current_key is not None
            case mode:
                raise AlbertException(f"Unknown pagination mode {mode}.")

    def _update_params(self, *, data: dict[str, Any], count: int) -> bool:
        """Update pagination state from a response payload."""
        match self.mode:
            case PaginationMode.OFFSET:
                if count == 0:
                    return False
                # Some search endpoints (e.g. /projects/search) omit offset in the response;
                # advance from the request offset we sent instead.
                self._pagination_params["offset"] = self._next_request_offset(
                    data=data, count=count
                )
            case PaginationMode.KEY:
                last_key = data.get("lastKey")
                self._last_key = last_key
                if not last_key:
                    return False
                self._pagination_params["startKey"] = last_key
            case mode:
                raise AlbertException(f"Unknown pagination mode {mode}.")
        return True

    def __iter__(self) -> Iterator[ItemType]:
        """Return the iterator instance."""
        return self

    def __next__(self) -> ItemType:
        """Return the next item from the iterator."""
        return next(self._iterator)

    def _request(self):
        """Issue a request for the next page."""
        if self.method == "GET":
            return self.session.get(self.path, params=self.params)
        payload = self._serialize_payload(self.json)
        return self.session.request(self.method, self.path, params=self.params, json=payload)

    def _serialize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Serialize a JSON payload for a request."""

        def convert(value):
            if isinstance(value, bool):
                return value
            if hasattr(value, "value"):
                return value.value
            if isinstance(value, list):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value

        return {k: convert(v) for k, v in payload.items() if v is not None}


class MetadataPreservingIterator(Iterator[OutType]):
    """Yield from ``items`` while exposing ``has_more`` / ``total`` from ``source``.

    Use whenever a ``get_all`` wraps a search paginator in custom iteration (batch
    hydration, etc.). A plain generator would drop those completeness signals.
    """

    def __init__(self, source: Any, items: Iterator[OutType]):
        self._source = source
        self._iterator = iter(items)

    @property
    def has_more(self) -> bool:
        """Delegate to the source paginator when present."""
        return bool(getattr(self._source, "has_more", False))

    @property
    def total(self) -> int | None:
        """Delegate to the source paginator when present."""
        return getattr(self._source, "total", None)

    def __iter__(self) -> Iterator[OutType]:
        return self

    def __next__(self) -> OutType:
        return next(self._iterator)


class MappedPaginator(MetadataPreservingIterator[OutType]):
    """Map items from a source iterator while preserving ``has_more`` / ``total``.

    Use for ``get_all`` methods that hydrate each ``search`` hit via ``get_by_id``.
    """

    def __init__(
        self,
        source: Iterator[Any],
        map_fn: Callable[[Any], OutType | None],
    ):
        def _mapped() -> Iterator[OutType]:
            for item in source:
                mapped = map_fn(item)
                if mapped is not None:
                    yield mapped

        super().__init__(source, _mapped())


class AsyncAlbertPaginator(AsyncIterator[ItemType]):
    """
    Async iterator for key-based paginated Albert endpoints.

    Parameters
    ----------
    session : AsyncAlbertSession
        The async session used to make requests.
    path : str
        Endpoint path to paginate.
    deserialize : Callable[[dict], ItemType]
        Function to convert each raw item dict into a model instance.
    params : dict[str, Any] | None, optional
        Initial query parameters.
    max_items : int | None, optional
        Stop after yielding this many items.
    """

    def __init__(
        self,
        *,
        session: AsyncAlbertSession,
        path: str,
        deserialize: Callable[[dict], ItemType],
        params: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        self._session = session
        self._path = path
        self._deserialize = deserialize
        self._params = dict(params or {})
        self._max_items = max_items
        self._has_more = False
        self._iterator = self._create_iterator()

    @property
    def has_more(self) -> bool:
        """True when iteration stopped early and more matching items are known to exist."""
        return self._has_more

    async def _create_iterator(self) -> AsyncIterator[ItemType]:
        yielded = 0
        while True:
            response = await self._session.get(self._path, params=self._params)
            data = response.json()
            items = data.get("Items", [])
            for item in items:
                if self._max_items is not None and yielded >= self._max_items:
                    self._has_more = True
                    return
                yield self._deserialize(item)
                yielded += 1
            key = data.get("lastKey")
            if self._max_items is not None and yielded >= self._max_items:
                self._has_more = key is not None and bool(items)
                return
            if not key or not items:
                break
            self._params["startKey"] = key

    def __aiter__(self) -> AsyncIterator[ItemType]:
        return self

    async def __anext__(self) -> ItemType:
        return await self._iterator.__anext__()
