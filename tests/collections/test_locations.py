import uuid

from albert.client import Albert
from albert.resources.locations import Location


def assert_valid_location_items(returned_list: list[Location]):
    """Assert that all returned items are valid Location objects."""
    assert returned_list, "Expected at least one Location"
    for c in returned_list[:10]:
        assert isinstance(c, Location)
        assert isinstance(c.name, str)
        assert c.id.startswith("LOC")


def test_location_get_all_with_filters(client: Albert):
    """Test locations.get_all() with country filter."""
    results = list(client.locations.get_all(country="US", max_items=10))
    assert_valid_location_items(results)


def test_location_get_all_with_pagination(client: Albert):
    """Test pagination in locations.get_all()."""
    results = list(client.locations.get_all(max_items=10))
    assert_valid_location_items(results)
    assert len(results) <= 10


def test_get_by_id(client: Albert, seeded_locations: list[Location]):
    # Assuming we want to get the first seeded location by ID
    seeded_location = seeded_locations[0]
    fetched_location = client.locations.get_by_id(id=seeded_location.id)

    assert isinstance(fetched_location, Location)
    assert fetched_location.id == seeded_location.id
    assert fetched_location.name == seeded_location.name


def test_list_by_ids(client: Albert, seeded_locations: list[Location]):
    ids = [loc.id for loc in seeded_locations]
    listed_locations = list(client.locations.get_all(ids=ids))

    assert len(listed_locations) == len(seeded_locations)
    assert {x.id for x in listed_locations} == {x.id for x in seeded_locations}


def test_create_location(
    caplog, client: Albert, seed_prefix: str, seeded_locations: list[Location]
):
    """Test creating a new location."""
    new_location = Location(
        name=seed_prefix,
        latitude=seeded_locations[0].latitude,
        longitude=-seeded_locations[0].longitude,
        address=seeded_locations[0].address,
    )

    created_location = client.locations.create(location=new_location)
    assert isinstance(created_location, Location)
    assert created_location.name == new_location.name
    assert created_location.latitude == new_location.latitude
    assert created_location.longitude == new_location.longitude


def test_get_or_create_location(client: Albert, seeded_locations: list[Location]):
    """Test get_or_create returns existing location."""
    existing = client.locations.get_by_id(id=seeded_locations[0].id)
    returned_location = client.locations.get_or_create(location=existing)

    assert isinstance(returned_location, Location)
    assert returned_location.id == existing.id
    assert returned_location.name == existing.name


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
    exists = client.locations.exists(location=seeded_location)

    assert exists is not None
    assert isinstance(exists, Location)
    assert exists.name == seeded_location.name


def test_delete_location(client: Albert, seeded_locations: list[Location]):
    # Create a new location to delete

    client.locations.delete(id=seeded_locations[2].id)

    # Ensure it no longer exists
    does_exist = client.locations.exists(location=seeded_locations[2])
    assert does_exist is None
