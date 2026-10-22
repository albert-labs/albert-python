"""Unit tests for the design-spaces collection's private helpers: cursor pagination."""

from urllib.parse import parse_qs, urlparse

import responses

from albert.collections.design_spaces import _LastKeyCursorPaginator
from albert.core.pagination import PaginationMode
from tests.unit.conftest import UNIT_BASE_URL

BASE = "/api/v4/design/design-spaces"

# --- _LastKeyCursorPaginator ---


def _listing(offline_session, pages: list[dict], **kwargs) -> _LastKeyCursorPaginator:
    for page in pages:
        responses.add(responses.GET, f"{UNIT_BASE_URL}{BASE}", json=page)
    return _LastKeyCursorPaginator(
        mode=PaginationMode.KEY,
        path=BASE,
        session=offline_session,
        params={"parentId": "PRO456"},
        deserialize=lambda items: [item["id"] for item in items],
        **kwargs,
    )


def _sent_cursors() -> list[str | None]:
    return [
        parse_qs(urlparse(call.request.url).query).get("lastKey", [None])[0]
        for call in responses.calls
    ]


@responses.activate
def test_last_key_paginator_sends_the_cursor_back_as_last_key(offline_session):
    """Test that each page's lastKey is sent back as lastKey until a page has none."""
    pager = _listing(
        offline_session,
        [{"items": [{"id": 1}, {"id": 2}], "lastKey": "k1"}, {"items": [{"id": 3}]}],
    )

    assert list(pager) == [1, 2, 3]
    assert _sent_cursors() == [None, "k1"]
    assert pager.has_more is False


@responses.activate
def test_last_key_paginator_reports_more_when_max_items_stops_early(offline_session):
    """Test that stopping at max_items with a cursor in hand reports more results."""
    pager = _listing(
        offline_session, [{"items": [{"id": 1}, {"id": 2}], "lastKey": "k1"}], max_items=1
    )

    assert list(pager) == [1]
    assert len(responses.calls) == 1
    assert pager.has_more is True


@responses.activate
def test_last_key_paginator_stops_on_a_repeated_cursor(offline_session):
    """Test that a page repeating an already-seen lastKey ends iteration."""
    pager = _listing(
        offline_session,
        [{"items": [{"id": 1}], "lastKey": "k1"}, {"items": [{"id": 2}], "lastKey": "k1"}],
    )

    assert list(pager) == [1]
    assert _sent_cursors() == [None, "k1"]
