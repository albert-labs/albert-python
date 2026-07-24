"""Paginator completeness tests (``has_more`` / ``total``).

These exercise the pagination state machine with scripted responses so edge cases
(broken offset backends, KEY-mode lastKey, mid-page caps) stay deterministic.
"""

from __future__ import annotations

from typing import Any

from albert.collections.cas import CasPaginator
from albert.core.pagination import (
    AlbertPaginator,
    AsyncAlbertPaginator,
    MappedPaginator,
    MetadataPreservingIterator,
)
from albert.core.shared.enums import PaginationMode


class _JsonResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def json(self) -> dict[str, Any]:
        return self._data


class _ScriptedSession:
    """Minimal session that returns a fixed sequence of JSON page payloads."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = list(pages)
        self.requests: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def get(self, path: str, params: dict[str, Any] | None = None, **kwargs: Any) -> _JsonResponse:
        self.requests.append({"method": "GET", "path": path, "params": params})
        return _JsonResponse(self._pages.pop(0))

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> _JsonResponse:
        self.requests.append({"method": method, "path": path, "params": params, "json": json})
        return _JsonResponse(self._pages.pop(0))


class _AsyncScriptedSession:
    """Async counterpart of ``_ScriptedSession`` for ``AsyncAlbertPaginator``."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = list(pages)
        self.requests: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    async def get(
        self, path: str, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> _JsonResponse:
        self.requests.append({"method": "GET", "path": path, "params": params})
        return _JsonResponse(self._pages.pop(0))


def _page(
    items: list[int],
    *,
    offset: int | None = None,
    total: int | str | None = None,
    last_key: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"Items": [{"id": i} for i in items]}
    if offset is not None:
        data["offset"] = offset
    if total is not None:
        data["total"] = total
    if last_key is not None:
        data["lastKey"] = last_key
    return data


def _cas_page(count: int) -> dict[str, Any]:
    """A CAS listing page whose items deserialize into ``Cas`` (needs ``number``)."""
    return {
        "Items": [{"id": f"CAS{i}", "number": f"{i}-00-0"} for i in range(count)],
    }


def test_offset_pagination_when_response_omits_offset() -> None:
    """Projects search often returns Items without echoing offset — still paginate."""
    session = _ScriptedSession(
        [
            _page(list(range(25))),
            _page(list(range(25, 35))),
            _page([]),
        ]
    )

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc"},
    )
    items = list(pag)

    assert len(items) == 35
    assert pag.has_more is False
    assert session.call_count == 3
    # Params dict is mutated in place; final offset reflects two full pages consumed.
    assert pag.params["offset"] == 35


def test_pages_past_a_full_first_page() -> None:
    """A full first page is not the end; keep paging until an empty page."""
    session = _ScriptedSession(
        [
            _page(list(range(1000))),
            _page(list(range(1000, 2000))),
            _page([]),
        ]
    )

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )
    items = list(pag)

    assert len(items) == 2000
    assert pag.has_more is False
    assert session.call_count == 3


def test_has_more_false_when_max_items_equals_known_total() -> None:
    """Full final page with known total — complete, not truncated."""
    session = _ScriptedSession([_page(list(range(1000)), offset=0, total=1000)])

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
        max_items=1000,
    )
    items = list(pag)

    assert len(items) == 1000
    assert pag.has_more is False
    assert pag.total == 1000


def test_has_more_true_when_max_items_hits_full_page_boundary() -> None:
    """A full page (count == limit) at the cap signals more likely exist, no extra request."""
    session = _ScriptedSession([_page(list(range(25)))])

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 25},
        max_items=25,
    )
    items = list(pag)

    assert len(items) == 25
    assert pag.has_more is True
    # No probe request: the caller sees exactly the pages it asked for.
    assert session.call_count == 1


def test_has_more_false_when_max_items_hits_short_page_without_total() -> None:
    """A short page at the cap with no total is a natural end, not a truncation."""
    session = _ScriptedSession([_page(list(range(25)))])

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
        max_items=25,
    )
    items = list(pag)

    assert len(items) == 25
    assert pag.has_more is False
    assert session.call_count == 1


def test_has_more_true_when_max_items_cuts_off_mid_page() -> None:
    """Stopping mid-page leaves an unyielded item, a definitive signal more exist."""
    session = _ScriptedSession([_cas_page(50)])

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
        max_items=30,
    )
    items = list(pag)

    assert len(items) == 30
    assert pag.has_more is True


def test_has_more_false_before_iteration() -> None:
    """has_more is a post-iteration signal; a fresh paginator reports False."""
    session = _ScriptedSession([_page(list(range(5)))])

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )

    assert pag.has_more is False
    assert pag.total is None


def test_has_more_when_offset_broken_but_total_exceeds_page() -> None:
    """Backend ignores limit (25/page) and returns empty for offset>0 — still not complete."""
    session = _ScriptedSession(
        [
            _page(list(range(25)), offset=0, total="15184"),
            _page([], offset=25, total="15184"),
        ]
    )

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )
    items = list(pag)

    assert len(items) == 25
    assert pag.has_more is True
    assert pag.total == 15184


def test_mapped_paginator_preserves_has_more_and_total() -> None:
    """get_all hydration wrappers must not drop the search paginator's completeness."""
    session = _ScriptedSession(
        [
            _page(list(range(25)), offset=0, total="15184"),
            _page([], offset=25, total="15184"),
        ]
    )

    source = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )
    mapped = MappedPaginator(source, lambda item: {"hydrated": item["id"]})
    items = list(mapped)

    assert len(items) == 25
    assert mapped.has_more is True
    assert mapped.total == 15184


def test_metadata_preserving_iterator_for_batch_hydration() -> None:
    """Batch-hydrating get_all (e.g. data_templates) must keep source has_more/total."""
    session = _ScriptedSession(
        [
            _page(list(range(25)), offset=0, total="5964"),
            _page([], offset=25, total="5964"),
        ]
    )

    source = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/datatemplates/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )

    def _batched():
        for item in source:
            yield {"hydrated": item["id"]}

    wrapped = MetadataPreservingIterator(source, _batched())
    items = list(wrapped)

    assert len(items) == 25
    assert wrapped.has_more is True
    assert wrapped.total == 5964


def test_mapped_paginator_drops_none_without_affecting_completeness() -> None:
    """map_fn returning None (e.g. a hit that failed to hydrate) drops the item only."""
    session = _ScriptedSession(
        [
            _page(list(range(10)), offset=0, total=10),
            _page([], offset=10, total=10),
        ]
    )

    source = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc", "limit": 1000},
    )
    # Drop every odd id.
    mapped = MappedPaginator(source, lambda item: item if item["id"] % 2 == 0 else None)
    items = list(mapped)

    assert [i["id"] for i in items] == [0, 2, 4, 6, 8]
    assert mapped.has_more is False
    assert mapped.total == 10


def test_key_mode_has_more_true_when_max_items_hits_full_page_with_last_key() -> None:
    """KEY mode: a full page plus a continuation key at the cap means more exist."""
    session = _ScriptedSession([_page(list(range(10)), last_key="KEY1")])

    pag = AlbertPaginator(
        mode=PaginationMode.KEY,
        path="/api/v3/cas",
        session=session,
        deserialize=lambda items: items,
        max_items=10,
    )
    items = list(pag)

    assert len(items) == 10
    assert pag.has_more is True
    assert session.call_count == 1


def test_key_mode_has_more_false_on_empty_last_key_at_cap() -> None:
    """KEY mode: an empty-string lastKey is terminal, matching page advancement."""
    session = _ScriptedSession([_page(list(range(10)), last_key="")])

    pag = AlbertPaginator(
        mode=PaginationMode.KEY,
        path="/api/v3/cas",
        session=session,
        deserialize=lambda items: items,
        max_items=10,
    )
    items = list(pag)

    assert len(items) == 10
    assert pag.has_more is False


def test_key_mode_has_more_false_on_natural_end() -> None:
    """KEY mode: no lastKey ends iteration with has_more False."""
    session = _ScriptedSession([_page(list(range(5)))])

    pag = AlbertPaginator(
        mode=PaginationMode.KEY,
        path="/api/v3/cas",
        session=session,
        deserialize=lambda items: items,
    )
    items = list(pag)

    assert len(items) == 5
    assert pag.has_more is False


def test_cas_paginator_short_final_page_at_cap_is_complete() -> None:
    """CasPaginator (startKey offset, limit 50): a short final page at the cap is complete.

    Regression: the removed offset-probe re-served the current page for startKey
    pagination and reported has_more True on every capped CAS search.
    """
    session = _ScriptedSession([_cas_page(30)])

    pag = CasPaginator(
        path="/api/v3/cas",
        session=session,
        params={"number": "7727"},
        max_items=30,
    )
    items = list(pag)

    assert len(items) == 30
    assert pag.has_more is False
    # No hidden probe request.
    assert session.call_count == 1


def test_cas_paginator_full_page_at_cap_signals_more() -> None:
    """CasPaginator: a full 50-item page at the cap signals more likely exist."""
    session = _ScriptedSession([_cas_page(50)])

    pag = CasPaginator(
        path="/api/v3/cas",
        session=session,
        params={"number": "7727"},
        max_items=50,
    )
    items = list(pag)

    assert len(items) == 50
    assert pag.has_more is True
    assert session.call_count == 1


async def test_async_paginator_has_more_true_at_cap_with_last_key() -> None:
    """Async KEY paginator sets has_more when the cap coincides with a continuation key."""
    session = _AsyncScriptedSession([_page(list(range(10)), last_key="KEY1")])

    pag = AsyncAlbertPaginator(
        session=session,
        path="/api/v3/chat/sessions",
        deserialize=lambda item: item,
        max_items=10,
    )
    items = [item async for item in pag]

    assert len(items) == 10
    assert pag.has_more is True


async def test_async_paginator_empty_last_key_is_terminal() -> None:
    """Async KEY paginator: an empty-string lastKey at the cap is not a continuation."""
    session = _AsyncScriptedSession([_page(list(range(10)), last_key="")])

    pag = AsyncAlbertPaginator(
        session=session,
        path="/api/v3/chat/sessions",
        deserialize=lambda item: item,
        max_items=10,
    )
    items = [item async for item in pag]

    assert len(items) == 10
    assert pag.has_more is False
