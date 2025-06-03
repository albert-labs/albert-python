from albert.albert import Albert
from albert.collections.base import OrderBy
from albert.resources.units import Unit, UnitCategory


def _list_asserts(returned_list):
    found = False
    for i, u in enumerate(returned_list):
        if i == 100:
            break
        assert isinstance(u, Unit)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("UNI")
        found = True
    assert found


def test_simple_units_list(client: Albert):
    simple_list = client.units.list()
    _list_asserts(simple_list)


def test_advanced_units_list(client: Albert, seeded_units: list[Unit]):
    test_unit = seeded_units[1]
    adv_list = client.units.list(
        name=test_unit.name,
        category=test_unit.category,
        order_by=OrderBy.ASCENDING,
        exact_match=True,
        verified=test_unit.verified,
    )
    adv_list = list(adv_list)
    for u in adv_list:
        assert test_unit.name.lower() in u.name.lower()
    _list_asserts(adv_list)

    adv_short_list = client.units.list(limit=2)
    _list_asserts(adv_short_list)


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
    assert client.units.unit_exists(name=test_unit.name)
    assert not client.units.unit_exists(
        name="totally nonesense unit no one should be using!662378393278932y5r"
    )


def test_unit_crud(client: Albert):
    new_unit = Unit(
        name="SDK Test Unit",
        symbol="x",
        synonyms=["kfnehiuow", "hbfuiewhbuewf89fy89b"],
        category=UnitCategory.MASS,
    )
    created_unit = client.units.create(unit=new_unit)
    assert isinstance(created_unit, Unit)
    assert created_unit.name == "SDK Test Unit"
    assert created_unit.id is not None

    created_unit.symbol = "y"
    updated_unit = client.units.update(unit=created_unit)
    assert isinstance(updated_unit, Unit)
    assert updated_unit.id == created_unit.id
    assert updated_unit.symbol == "y"

    client.units.delete(id=updated_unit.id)
    assert not client.units.unit_exists(name=updated_unit.name)


def test_create_unit(caplog, seeded_units: list[Unit], client: Albert):
    dupe_unit = Unit(
        name=seeded_units[0].name,
        symbol=seeded_units[0].symbol,
    )

    registered = client.units.create(unit=dupe_unit)
    assert registered.id == seeded_units[0].id
    assert (
        f"Unit with the name {seeded_units[0].name} already exists. Returning the existing unit."
        in caplog.text
    )
