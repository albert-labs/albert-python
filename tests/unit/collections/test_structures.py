"""Unit tests for the structures collection's client-side logic."""

import pytest
from pydantic import ValidationError

from albert.collections.structures import (
    AsyncStructureCollection,
    StructureCollection,
    _build_get_by_ids_params,
)
from albert.core.async_session import AsyncAlbertSession
from albert.resources.structures import StructureField
from tests.unit.conftest import UNIT_BASE_URL

# --- _build_get_by_ids_params ---


def test_build_params_joins_ids_as_csv():
    """Test that structure IDs are joined into a single comma-separated value."""
    params = _build_get_by_ids_params(structure_ids=["STT1", "STT2"], required_fields=None)

    assert params == {"structureId": "STT1,STT2"}


def test_build_params_joins_required_fields_as_csv():
    """Test that required fields are sent as their comma-separated wire values."""
    params = _build_get_by_ids_params(
        structure_ids=["STT1"],
        required_fields=[StructureField.SMILES, StructureField.INCHI_KEY],
    )

    assert params == {"structureId": "STT1", "requiredFields": "smiles,inchiKey"}


def test_build_params_omits_required_fields_when_empty():
    """Test that an empty required-fields list sends no requiredFields parameter."""
    params = _build_get_by_ids_params(structure_ids=["STT1"], required_fields=[])

    assert params == {"structureId": "STT1"}


def test_build_params_accepts_exactly_25_ids():
    """Test that 25 IDs, the maximum accepted, do not raise."""
    params = _build_get_by_ids_params(
        structure_ids=[f"STT{i}" for i in range(25)], required_fields=None
    )

    assert params["structureId"].count(",") == 24


def test_build_params_raises_above_25_ids():
    """Test that more than 25 IDs raise a ValueError before any call is made."""
    with pytest.raises(ValueError, match="At most 25 structure IDs"):
        _build_get_by_ids_params(
            structure_ids=[f"STT{i}" for i in range(26)], required_fields=None
        )


# --- get_by_ids client-side behavior ---


def test_get_by_ids_returns_empty_list_for_empty_ids(offline_session):
    """Test that an empty ID list returns no structures without raising."""
    collection = StructureCollection(session=offline_session)

    assert collection.get_by_ids(structure_ids=[]) == []


def test_get_by_ids_raises_above_25_ids(offline_session):
    """Test that the public method rejects more than 25 IDs."""
    collection = StructureCollection(session=offline_session)

    with pytest.raises(ValueError, match="At most 25 structure IDs"):
        collection.get_by_ids(structure_ids=[f"STT{i}" for i in range(26)])


def test_get_by_ids_rejects_unknown_required_field(offline_session):
    """Test that an unknown required field fails validation."""
    collection = StructureCollection(session=offline_session)

    with pytest.raises(ValidationError):
        collection.get_by_ids(structure_ids=["STT1"], required_fields=["bogus"])


async def test_async_get_by_ids_returns_empty_list_for_empty_ids():
    """Test that the async collection returns no structures for an empty ID list."""
    collection = AsyncStructureCollection(
        session=AsyncAlbertSession(base_url=UNIT_BASE_URL, token="unit-token")
    )

    assert await collection.get_by_ids(structure_ids=[]) == []


async def test_async_get_by_ids_raises_above_25_ids():
    """Test that the async collection rejects more than 25 IDs."""
    collection = AsyncStructureCollection(
        session=AsyncAlbertSession(base_url=UNIT_BASE_URL, token="unit-token")
    )

    with pytest.raises(ValueError, match="At most 25 structure IDs"):
        await collection.get_by_ids(structure_ids=[f"STT{i}" for i in range(26)])
