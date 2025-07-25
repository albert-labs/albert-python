from albert.client import Albert
from albert.core.shared.enums import OrderBy
from albert.resources.units import Unit, UnitCategory


def assert_unit_items(returned_list: list[Unit]):
    for u in returned_list[:10]:
        assert isinstance(u, Unit)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("UNI")


def test_units_get_all_with_pagination(client: Albert):
    """Test retrieving units with pagination and max_items control."""
    paginated = list(client.units.get_all(max_items=10))
    assert_unit_items(paginated)
    assert len(paginated) <= 10


def test_units_get_all_with_filters(client: Albert, seeded_units: list[Unit]):
    """Test filtered retrieval of units using name, category, and verification flag."""
    test_unit = seeded_units[1]
    filtered = list(
        client.units.get_all(
            name=test_unit.name,
            category=test_unit.category,
            order_by=OrderBy.ASCENDING,
            exact_match=True,
            verified=test_unit.verified,
            max_items=10,
        )
    )
    for u in filtered:
        assert test_unit.name.lower() in u.name.lower()
    assert_unit_items(filtered)


def test_units_get_all_limited_batch(client: Albert):
    """Test small result batch retrieval with max_items."""
    short_list = list(client.units.get_all(max_items=2))
    assert_unit_items(short_list)
    assert len(short_list) <= 2


def test_get_unit(client: Albert, seeded_units: list[Unit]):
    test_unit = seeded_units[0]
    unit = client.units.get_by_name(name=test_unit.name)
    assert isinstance(unit, Unit)

    by_id = client.units.get_by_id(id=unit.id)
    assert isinstance(by_id, Unit)
    assert by_id.name.lower() == test_unit.name.lower()


def test_bulk_get(client: Albert, seeded_units: list[Unit]):
    fetched_units = client.units.get_by_ids(ids=[u.id for u in seeded_units])
    assert len(fetched_units) == len(seeded_units)
    assert {u.id for u in fetched_units} == {u.id for u in seeded_units}


def test_unit_exists(client: Albert, seeded_units: list[Unit]):
    test_unit = seeded_units[2]
    assert client.units.exists(name=test_unit.name)
    assert not client.units.exists(
        name="totally nonesense unit no one should be using!662378393278932y5r"
    )


def test_unit_crud(client: Albert, seed_prefix: str):
    new_unit = Unit(
        name=seed_prefix,
        symbol="x",
        synonyms=["kfnehiuow", "hbfuiewhbuewf89fy89b"],
        category=UnitCategory.MASS,
    )
    created_unit = client.units.create(unit=new_unit)
    assert isinstance(created_unit, Unit)
    assert created_unit.name == seed_prefix
    assert created_unit.id is not None

    created_unit.symbol = "y"
    updated_unit = client.units.update(unit=created_unit)
    assert isinstance(updated_unit, Unit)
    assert updated_unit.id == created_unit.id
    assert updated_unit.symbol == "y"

    client.units.delete(id=updated_unit.id)
    assert not client.units.exists(name=updated_unit.name)


def test_get_or_create_unit(caplog, seeded_units: list[Unit], client: Albert):
    dupe_unit = Unit(
        name=seeded_units[0].name,
        symbol=seeded_units[0].symbol,
    )

    registered = client.units.get_or_create(unit=dupe_unit)
    assert registered.id == seeded_units[0].id
    assert (
        f"Unit with the name {seeded_units[0].name} already exists. Returning the existing unit."
        in caplog.text
    )
