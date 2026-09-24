import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.unit_families_v4 import (
    UnitFamilyV4,
    UnitFamilyV4Lookup,
    UnitFamilyV4Origin,
    UnitFamilyV4SearchItem,
    UnitFamilyV4Type,
)
from tests.utils.wait import poll_until

pytestmark = pytest.mark.skip(
    reason="The v4 unit families API (master-data) is not yet available in the test environment."
)


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def test_create_get_update_delete_convertible(client: Albert, seed_prefix: str):
    """Test the full lifecycle of a convertible unit family created from a reference unit."""
    family = client.unit_families_v4.create(
        unit_family=UnitFamilyV4(
            name=f"{seed_prefix} - Mass {_suffix()}",
            type=UnitFamilyV4Type.CONVERTIBLE,
            ref_unit="kg",
        )
    )
    try:
        assert family.id
        assert family.origin == UnitFamilyV4Origin.CUSTOM
        assert family.si_unit == "kg"
        assert family.dimension

        fetched = poll_until(lambda: [client.unit_families_v4.get_by_id(id=family.id)])
        assert fetched and fetched[0].id == family.id
        assert fetched[0].units is not None

        fetched[0].description = "Updated by the SDK test suite"
        updated = client.unit_families_v4.update(unit_family=fetched[0])
        assert updated.description == "Updated by the SDK test suite"
    finally:
        with suppress(NotFoundError):
            client.unit_families_v4.delete(id=family.id)


def test_create_convertible_by_expression(client: Albert, seed_prefix: str):
    """Test creating a convertible family from a unit expression."""
    family = client.unit_families_v4.create(
        unit_family=UnitFamilyV4(
            name=f"{seed_prefix} - Force {_suffix()}",
            type=UnitFamilyV4Type.CONVERTIBLE,
            unit_expression="kg*m/s^2",
        )
    )
    try:
        assert family.si_unit
        assert family.type == UnitFamilyV4Type.CONVERTIBLE
    finally:
        with suppress(NotFoundError):
            client.unit_families_v4.delete(id=family.id)


def test_search_and_get_by_ids(client: Albert, seed_prefix: str):
    """Test search scoped to a private family and bulk retrieval by ID."""
    family = client.unit_families_v4.create(
        unit_family=UnitFamilyV4(
            name=f"{seed_prefix} - Count {_suffix()}", type=UnitFamilyV4Type.NON_CONVERTIBLE
        )
    )
    try:
        found = poll_until(
            lambda: [
                f
                for f in client.unit_families_v4.search(text=seed_prefix, max_items=100)
                if f.id == family.id
            ]
        )
        assert found, "Expected the created family in search results"
        assert isinstance(found[0], UnitFamilyV4SearchItem)

        by_ids = poll_until(lambda: client.unit_families_v4.get_by_ids(ids=[family.id]))
        assert [f.id for f in by_ids] == [family.id]
    finally:
        with suppress(NotFoundError):
            client.unit_families_v4.delete(id=family.id)


def test_search_filters(client: Albert):
    """Test type and origin filters on unit family search."""
    results = list(
        client.unit_families_v4.search(
            type=[UnitFamilyV4Type.CONVERTIBLE],
            origin=[UnitFamilyV4Origin.ALBERT_MANAGED],
            max_items=10,
        )
    )
    assert results
    for family in results:
        assert family.type == UnitFamilyV4Type.CONVERTIBLE
        assert family.origin == UnitFamilyV4Origin.ALBERT_MANAGED


def test_lookup(client: Albert):
    """Test name lookup returns a UnitFamilyV4Lookup."""
    result = client.unit_families_v4.lookup(name="Mass")
    assert isinstance(result, UnitFamilyV4Lookup)
    assert result.exists is True

    result = client.unit_families_v4.lookup(name=f"does-not-exist-{_suffix()}")
    assert result.exists is False
