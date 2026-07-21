"""Unit tests for AlbertPaginator offset continuation."""

from unittest.mock import MagicMock

from albert.core.pagination import (
    AlbertPaginator,
    MappedPaginator,
    MetadataPreservingIterator,
)
from albert.core.shared.enums import PaginationMode


def _page(
    items: list[int],
    *,
    offset: int | None = None,
    total: int | str | None = None,
) -> MagicMock:
    data: dict = {"Items": [{"id": i} for i in items]}
    if offset is not None:
        data["offset"] = offset
    if total is not None:
        data["total"] = total
    resp = MagicMock()
    resp.json.return_value = data
    return resp


def test_offset_pagination_when_response_omits_offset() -> None:
    """Projects search often returns Items without echoing offset — still paginate."""
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(25))),
        _page(list(range(25, 35))),
        _page([]),
    ]

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
    assert session.get.call_count == 3
    # Params dict is mutated in place; final offset reflects two full pages consumed.
    assert pag.params["offset"] == 35


def test_pages_past_a_full_first_page() -> None:
    """A full first page is not the end; keep paging until an empty page."""
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(1000))),
        _page(list(range(1000, 2000))),
        _page([]),
    ]

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
    assert session.get.call_count == 3


def test_has_more_when_max_items_hits_short_page_without_offset_echo() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(25))),
        _page([999]),  # probe / continuation page
    ]

    pag = AlbertPaginator(
        mode=PaginationMode.OFFSET,
        path="/api/v3/projects/search",
        session=session,
        deserialize=lambda items: items,
        params={"order": "desc"},
        max_items=25,
    )
    items = list(pag)

    assert len(items) == 25
    assert pag.has_more is True


def test_has_more_when_offset_broken_but_total_exceeds_page() -> None:
    """Backend ignores limit (25/page) and returns empty for offset>0 — still not complete."""
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(25)), offset=0, total="15184"),
        _page([], offset=25, total="15184"),
    ]

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
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(25)), offset=0, total="15184"),
        _page([], offset=25, total="15184"),
    ]

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
    session = MagicMock()
    session.get.side_effect = [
        _page(list(range(25)), offset=0, total="5964"),
        _page([], offset=25, total="5964"),
    ]

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
