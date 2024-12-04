import uuid

from albert import Albert
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation


def _list_asserts(returned_list):
    found = False
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, StorageLocation)
        found = True
    assert found


def test_basic_lists(client: Albert):
    list_response = client.storage_locations.list()
    _list_asserts(list_response)


def test_advanced_list(
    client: Albert,
    seeded_storage_locations: list[StorageLocation],
    seeded_locations: list[Location],
):
    list_response = client.storage_locations.list(
        name=[seeded_storage_locations[0].name], exact_match=True
    )

    list_response = list(list_response)
    _list_asserts(list_response)
    for sl in list_response:
        assert sl.name == seeded_locations[0].name

    list_response = client.storage_locations.list(location=seeded_locations[0])
    list_response = list(list_response)
    _list_asserts(list_response)

    seeded_location_ids = {x.location.id for x in seeded_storage_locations}
    for sl in list_response:
        assert sl.location.id in seeded_location_ids


def test_pagination(client: Albert, seeded_storage_locations: list[StorageLocation]):
    list_response = client.storage_locations.list(limit=2)
    _list_asserts(list_response)


def test_avoids_dupes(caplog, client: Albert, seeded_storage_locations: list[StorageLocation]):
    sl = seeded_storage_locations[0].model_copy(update={"id": None})

    duped = client.storage_locations.create(storage_location=sl)
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
