import uuid

from albert import Albert
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation


def assert_valid_storage_location_items(returned_list: list[StorageLocation]):
    """Assert that returned items are valid StorageLocation instances."""
    assert returned_list, "Expected at least one StorageLocation result"
    for u in returned_list[:10]:
        assert isinstance(u, StorageLocation)


def test_storage_location_get_all_with_pagination(client: Albert):
    """Test storage location get_all."""
    results = list(client.storage_locations.get_all(max_items=10))
    assert_valid_storage_location_items(results)
    assert len(results) <= 10


def test_storage_location_get_all_with_filters(
    client: Albert,
    seeded_storage_locations: list[StorageLocation],
    seeded_locations: list[Location],
):
    """Test get_all with name and location filters."""
    name = seeded_storage_locations[0].name
    location = seeded_locations[0]

    results_by_name = list(
        client.storage_locations.get_all(name=[name], exact_match=True, max_items=10)
    )
    assert_valid_storage_location_items(results_by_name)
    for sl in results_by_name:
        assert sl.name == name

    results_by_location = list(client.storage_locations.get_all(location=location, max_items=10))
    assert_valid_storage_location_items(results_by_location)

    seeded_location_ids = {x.location.id for x in seeded_storage_locations}
    for sl in results_by_location:
        assert sl.location.id in seeded_location_ids


def test_get_or_create_storage_location(
    caplog, client: Albert, seeded_storage_locations: list[StorageLocation]
):
    sl = seeded_storage_locations[0].model_copy(update={"id": None})

    duped = client.storage_locations.get_or_create(storage_location=sl)
    assert (
        f"Storage location with name {sl.name} already exists, returning existing." in caplog.text
    )
    assert duped.id == seeded_storage_locations[0].id
    assert duped.name == seeded_storage_locations[0].name
    assert duped.location.id == seeded_storage_locations[0].location.id


def test_update(client: Albert, seeded_storage_locations: list[StorageLocation]):
    sl = seeded_storage_locations[0].model_copy()
    updated_name = f"TEST - {uuid.uuid4()}"
    sl.name = updated_name
    updated = client.storage_locations.update(storage_location=sl)
    assert updated.id == seeded_storage_locations[0].id
    assert updated.name == sl.name
