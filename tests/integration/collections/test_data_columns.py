from contextlib import suppress

import pytest

from albert import Albert
from albert.core.shared.enums import PaginationMode
from albert.exceptions import NotFoundError
from albert.resources.data_columns import DataColumn
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("datatemplates")


def assert_valid_data_column_items(returned_list: list[DataColumn], limit=100):
    """Assert that returned items are valid DataColumn instances."""
    assert returned_list, "Expected at least one DataColumn result"
    for u in returned_list[:limit]:
        assert isinstance(u, DataColumn)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("DAC")


def test_data_column_get_all_with_pagination(
    client: Albert, seeded_data_columns: list[DataColumn]
):
    """Test get_all with pagination for DataColumn."""
    results = list(client.data_columns.get_all(max_items=10))
    assert len(results) <= 10
    assert_valid_data_column_items(results)


def test_data_column_get_all_with_filters(client: Albert, seeded_data_columns: list[DataColumn]):
    """Test get_all filters by name with and without exact match."""
    name = seeded_data_columns[0].name

    results = poll_until(
        lambda: [
            dc
            for dc in client.data_columns.get_all(name=name, exact_match=False, max_items=10)
            if name.lower() in dc.name.lower()
        ]
    )
    assert results, "Expected seeded data column in filtered get_all results"
    assert_valid_data_column_items(results)

    no_match = list(
        client.data_columns.get_all(
            name="chaos tags 126485% HELLO WORLD!!!!", exact_match=True, max_items=5
        )
    )
    assert no_match == []


def test_data_column_get_all_by_ids(client: Albert, seeded_data_columns: list[DataColumn]):
    """Test get_all with specific list of DataColumn IDs."""
    ids = [x.id for x in seeded_data_columns]
    id_set = set(ids)
    for column_id in ids:
        fetched = client.data_columns.get_by_id(id=column_id)
        assert fetched.id == column_id

    results = poll_until(
        lambda: [
            dc for dc in client.data_columns.get_all(ids=ids, max_items=50) if dc.id in id_set
        ]
    )
    assert results, "Expected get_all(ids=...) to return seeded data columns"
    assert {x.id for x in results} <= id_set
    assert_valid_data_column_items(results)


def test_data_column_search_uses_cursor_pagination(
    client: Albert, seed_prefix: str, monkeypatch: pytest.MonkeyPatch
):
    """Test search returns all scoped matches exactly once across cursor pages."""
    monkeypatch.setattr("albert.core.pagination.DEFAULT_LIMIT", 1)
    data_columns = []
    try:
        for suffix in ("first", "second"):
            data_columns.append(
                client.data_columns.create(
                    data_column=DataColumn(name=f"{seed_prefix}-cursor-{suffix}")
                )
            )
        column_ids = [column.id for column in data_columns]

        def search_all_matches():
            results = client.data_columns.search(albert_id=column_ids)
            matches = list(results)
            assert results.mode == PaginationMode.SEARCH_AFTER
            assert results.json["limit"] == 1
            return matches

        matches = poll_until(
            search_all_matches,
            predicate=lambda items: sorted(item.id for item in items) == sorted(column_ids),
        )
        assert sorted(item.id for item in matches) == sorted(column_ids)

        early_results = client.data_columns.search(albert_id=column_ids, max_items=1)
        assert len(list(early_results)) == 1
        assert early_results.has_more
    finally:
        for column in data_columns:
            with suppress(NotFoundError):
                client.data_columns.delete(id=column.id)


def test_data_column_search(
    client: Albert, seed_prefix: str, seeded_data_columns: list[DataColumn]
):
    """Test search finds seeded data columns and hits hydrate to full DataColumn."""
    seeded_ids = {dc.id for dc in seeded_data_columns}
    hits = poll_until(
        lambda: [
            item
            for item in client.data_columns.search(text=seed_prefix, max_items=50)
            if item.id in seeded_ids
        ]
    )
    assert hits, "Expected seeded data columns in search results"
    hit = hits[0]
    assert hit.id in seeded_ids

    hydrated = hit.hydrate()
    assert isinstance(hydrated, DataColumn)
    assert hydrated.id == hit.id


def test_get_by_name(client: Albert, seeded_data_columns: list[DataColumn]):
    name = seeded_data_columns[0].name
    dc = client.data_columns.get_by_name(name=name)
    assert dc is not None
    assert dc.name == name
    assert dc.id == seeded_data_columns[0].id

    chaos_name = "JHByu8gt43278hixvy87H&*(#BIuyvd)"
    dc = client.data_columns.get_by_name(name=chaos_name)
    assert dc is None


def test_get_or_create_data_columns(client: Albert, seeded_data_columns: list[DataColumn]):
    """Test get_or_create returns an existing data column when one with the same name exists."""
    existing = seeded_data_columns[0]
    returned = client.data_columns.get_or_create(data_column=existing)
    assert isinstance(returned, DataColumn)
    assert returned.id == existing.id
    assert returned.name == existing.name


def test_update(client: Albert, seeded_data_columns: list[DataColumn], seed_prefix: str):
    dc = seeded_data_columns[0]
    new_name = f"{seed_prefix}-new name"
    dc.name = new_name
    updated_dc = client.data_columns.update(data_column=dc)
    assert updated_dc.name == new_name
    assert updated_dc.id == dc.id
