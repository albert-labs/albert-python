from pydantic import BaseModel

from albert.core.pagination import AlbertPaginator
from albert.core.shared.enums import PaginationMode


class _FakeItem(BaseModel):
    value: int


class _FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def json(self) -> dict:
        return self._data


class _FakeSession:
    """Minimal stand-in for AlbertSession; only `.get` is used by OFFSET pagination."""

    def __init__(self, pages: list[dict]):
        self._pages = pages
        self.calls = 0

    def get(self, path: str, params: dict | None = None) -> _FakeResponse:
        page = self._pages[self.calls]
        self.calls += 1
        return _FakeResponse(page)


def _deserialize(items):
    return [_FakeItem(**item).value for item in items]


def test_paginator_skips_unparseable_item_without_losing_page(caplog):
    """A single unparseable item must not discard the rest of its page.

    One malformed row in a 1000-item search page used to raise mid-`list(...)`
    and silently zero out the entire page.
    """
    session = _FakeSession(
        pages=[
            {
                "Items": [
                    {"albertId": "A1", "value": 1},
                    {"albertId": "A2", "value": "not-a-number"},
                    {"albertId": "A3", "value": 3},
                ],
                "offset": "0",
            },
            {"Items": [], "offset": "3"},
        ]
    )

    paginator = AlbertPaginator(
        path="/fake",
        mode=PaginationMode.OFFSET,
        session=session,
        deserialize=_deserialize,
    )

    with caplog.at_level("WARNING"):
        results = list(paginator)

    assert results == [1, 3]
    assert any("A2" in record.message for record in caplog.records)
