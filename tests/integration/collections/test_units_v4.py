import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type
from albert.resources.units_v4 import (
    UnitFamilyV4Ref,
    UnitV4,
    UnitV4Compatible,
    UnitV4Lookup,
    UnitV4Origin,
    UnitV4Type,
)
from tests.utils.wait import poll_until

pytestmark = pytest.mark.skip(
    reason="The v4 units API (master-data) is not yet available in the test environment."
)


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def test_create_get_update_delete_convertible(client: Albert, seed_prefix: str):
    """Test the full lifecycle of a convertible unit created from a reference unit."""
    suffix = _suffix()
    unit = client.units_v4.create(
        unit=UnitV4(
            name=f"{seed_prefix} - Kilogram {suffix}",
            symbol=f"kg{suffix}",
            type=UnitV4Type.CONVERTIBLE,
            ref_unit="kg",
        )
    )
    try:
        assert unit.id
        assert unit.type == UnitV4Type.CONVERTIBLE
        assert unit.origin == UnitV4Origin.CUSTOM
        assert unit.si_unit == "kg"
        assert unit.si_value is not None
        assert unit.unit_families

        fetched = poll_until(lambda: [client.units_v4.get_by_id(id=unit.id)])
        assert fetched and fetched[0].id == unit.id

        fetched[0].description = "Updated by the SDK test suite"
        fetched[0].synonyms = ["kilo", "kilos"]
        updated = client.units_v4.update(unit=fetched[0])
        assert updated.description == "Updated by the SDK test suite"
        assert set(updated.synonyms or []) == {"kilo", "kilos"}
    finally:
        with suppress(NotFoundError):
            client.units_v4.delete(id=unit.id)


def test_create_non_convertible_with_family(client: Albert, seed_prefix: str):
    """Test creating a non-convertible unit linked to a private unit family."""
    suffix = _suffix()
    family = client.unit_families_v4.create(
        unit_family=UnitFamilyV4(
            name=f"{seed_prefix} - Count {suffix}", type=UnitFamilyV4Type.NON_CONVERTIBLE
        )
    )
    unit = None
    try:
        unit = client.units_v4.create(
            unit=UnitV4(
                name=f"{seed_prefix} - Batch {suffix}",
                symbol=f"batch{suffix}",
                type=UnitV4Type.NON_CONVERTIBLE,
                unit_families=[UnitFamilyV4Ref(id=family.id)],
            )
        )
        assert unit.type == UnitV4Type.NON_CONVERTIBLE
        assert unit.si_unit is None
        assert {f.id for f in unit.unit_families or []} == {family.id}
    finally:
        with suppress(NotFoundError):
            if unit is not None:
                client.units_v4.delete(id=unit.id)
        with suppress(NotFoundError):
            client.unit_families_v4.delete(id=family.id)


def test_update_convertible_rejects_family_change(client: Albert, seed_prefix: str):
    """Test that changing unit families on a convertible unit raises before any request."""
    suffix = _suffix()
    unit = client.units_v4.create(
        unit=UnitV4(
            name=f"{seed_prefix} - Gram {suffix}",
            symbol=f"g{suffix}",
            type=UnitV4Type.CONVERTIBLE,
            ref_unit="g",
        )
    )
    try:
        fetched = poll_until(lambda: [client.units_v4.get_by_id(id=unit.id)])[0]
        fetched.unit_families = [UnitFamilyV4Ref(id="UNF-does-not-matter")]
        with pytest.raises(ValueError):
            client.units_v4.update(unit=fetched)
    finally:
        with suppress(NotFoundError):
            client.units_v4.delete(id=unit.id)


def test_search_and_get_by_ids(client: Albert, seed_prefix: str):
    """Test search scoped to a private unit and bulk retrieval by ID."""
    suffix = _suffix()
    unit = client.units_v4.create(
        unit=UnitV4(
            name=f"{seed_prefix} - Meter {suffix}",
            symbol=f"m{suffix}",
            type=UnitV4Type.CONVERTIBLE,
            ref_unit="m",
        )
    )
    try:
        found = poll_until(
            lambda: [
                u
                for u in client.units_v4.search(text=seed_prefix, max_items=100)
                if u.id == unit.id
            ]
        )
        assert found, "Expected the created unit in search results"

        by_ids = poll_until(lambda: client.units_v4.get_by_ids(ids=[unit.id]))
        assert [u.id for u in by_ids] == [unit.id]
    finally:
        with suppress(NotFoundError):
            client.units_v4.delete(id=unit.id)


def test_search_pagination(client: Albert):
    """Test max_items cap and has_more on the units search paginator."""
    paginator = client.units_v4.search(max_items=5)
    results = list(paginator)
    assert len(results) <= 5
    assert all(isinstance(u, UnitV4) for u in results)
    if len(results) == 5:
        assert paginator.total is None or paginator.total >= 5


def test_lookup(client: Albert):
    """Test symbol and name lookups return a UnitV4Lookup."""
    result = client.units_v4.lookup(symbol="kg")
    assert isinstance(result, UnitV4Lookup)
    assert result.exists is True

    result = client.units_v4.lookup(name=f"does-not-exist-{_suffix()}")
    assert result.exists is False


def test_lookup_requires_exactly_one_filter(client: Albert):
    """Test that lookup raises when zero or two identifiers are provided."""
    with pytest.raises(ValueError):
        client.units_v4.lookup()
    with pytest.raises(ValueError):
        client.units_v4.lookup(symbol="kg", name="Kilogram")


def test_get_compatible(client: Albert):
    """Test resolving an SI mapping by symbol and by expression."""
    by_symbol = client.units_v4.get_compatible(symbol="g")
    assert isinstance(by_symbol, UnitV4Compatible)
    assert by_symbol.si_unit == "kg"

    by_expression = client.units_v4.get_compatible(expression="1000*g")
    assert by_expression.si_unit == "kg"
    assert by_expression.ref_unit_value is not None


def test_get_compatible_requires_exactly_one_filter(client: Albert):
    """Test that get_compatible raises when zero or two inputs are provided."""
    with pytest.raises(ValueError):
        client.units_v4.get_compatible()
    with pytest.raises(ValueError):
        client.units_v4.get_compatible(symbol="g", expression="1000*g")
