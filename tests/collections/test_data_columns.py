from albert import Albert
from albert.resources.data_columns import DataColumn


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

    results = list(client.data_columns.get_all(name=name, exact_match=False, max_items=10))
    assert any(name.lower() in dc.name.lower() for dc in results)
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
    results = list(client.data_columns.get_all(ids=ids, max_items=50))

    assert len(results) == len(ids)
    assert {x.id for x in results} == set(ids)
    assert_valid_data_column_items(results)


def test_get_by_name(client: Albert, seeded_data_columns: list[DataColumn]):
    name = seeded_data_columns[0].name
    dc = client.data_columns.get_by_name(name=name)
    assert dc is not None
    assert dc.name == name
    assert dc.id == seeded_data_columns[0].id

    chaos_name = "JHByu8gt43278hixvy87H&*(#BIuyvd)"
    dc = client.data_columns.get_by_name(name=chaos_name)
    assert dc is None


def test_get_by_id(client: Albert, seeded_data_columns: list[DataColumn]):
    dc = client.data_columns.get_by_id(id=seeded_data_columns[0].id)
    assert dc.name == seeded_data_columns[0].name
    assert dc.id == seeded_data_columns[0].id


def test_update(client: Albert, seeded_data_columns: list[DataColumn], seed_prefix: str):
    dc = seeded_data_columns[0]
    new_name = f"{seed_prefix}-new name"
    dc.name = new_name
    updated_dc = client.data_columns.update(data_column=dc)
    assert updated_dc.name == new_name
    assert updated_dc.id == dc.id
