import uuid

from albert.albert import Albert
from albert.resources.locations import Location


def _list_asserts(returned_list):
    for i, c in enumerate(returned_list):
        if i == 30:
            break
        assert isinstance(c, Location)
        assert isinstance(c.name, str)
        assert c.id.startswith("LOC")


def test_simple_list(client: Albert):
    simple_loc_list = client.locations.list()
    _list_asserts(simple_loc_list)


def test_adv_list(client: Albert):
    adv_list = client.locations.list(country="US")
    _list_asserts(adv_list)
    short_list = client.locations.list(limit=2)
    _list_asserts(short_list)


def test_get_by_id(client: Albert, seeded_locations: list[Location]):
    # Assuming we want to get the first seeded location by ID
    seeded_location = seeded_locations[0]
    fetched_location = client.locations.get_by_id(id=seeded_location.id)

    assert isinstance(fetched_location, Location)
    assert fetched_location.id == seeded_location.id
    assert fetched_location.name == seeded_location.name


def test_list_by_ids(client: Albert, seeded_locations: list[Location]):
    ids = [loc.id for loc in seeded_locations]
    listed_locations = list(client.locations.list(ids=ids))

    assert len(listed_locations) == len(seeded_locations)
    assert {x.id for x in listed_locations} == {x.id for x in seeded_locations}


def test_create_location(caplog, client: Albert, seeded_locations: list[Location]):
    # Create a new location and check if it's created properly

    new_location = Location(
        name=seeded_locations[0].name,
        latitude=seeded_locations[0].latitude,
        longitude=-seeded_locations[0].longitude,
        address=seeded_locations[0].address,
    )

    created_location = client.locations.create(location=new_location)

    # assert it returns the existing
    re_created = client.locations.create(location=created_location)
    assert (
        f"Location with name {created_location.name} matches an existing location. Returning the existing Location."
        in caplog.text
    )
    assert re_created.id == seeded_locations[0].id


def test_update_location(client: Albert, seeded_locations: list[Location]):
    # Update the first seeded location
    seeded_location = seeded_locations[0]
    updated_name = f"TEST - {uuid.uuid4()}"
    updated_location = Location(
        name=updated_name,
        latitude=40.0,
        longitude=-75.0,
        address=seeded_location.address,
        id=seeded_location.id,
    )

    # Perform the update
    updated_loc = client.locations.update(location=updated_location)

    assert isinstance(updated_loc, Location)
    assert updated_loc.name == updated_name
    assert updated_loc.latitude == 40.0
    assert updated_loc.longitude == -75.0


def test_location_exists(client: Albert, seeded_locations):
    # Check if the first seeded location exists
    seeded_location = seeded_locations[1]
    exists = client.locations.location_exists(location=seeded_location)

    assert exists is not None
    assert isinstance(exists, Location)
    assert exists.name == seeded_location.name


def test_delete_location(client: Albert, seeded_locations: list[Location]):
    # Create a new location to delete

    client.locations.delete(id=seeded_locations[2].id)

    # Ensure it no longer exists
    does_exist = client.locations.location_exists(location=seeded_locations[2])
    assert does_exist is None
