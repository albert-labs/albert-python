"""Integration tests for the structures collections."""

import uuid

import pytest

from albert import Albert, AsyncAlbert
from albert.exceptions import BadRequestError, NotFoundError
from albert.resources.structures import StructureField


@pytest.fixture(scope="module")
def known_structure_id(client: Albert) -> str:
    """Discover an existing structure ID to look up in this environment."""
    data = client.session.get(
        "/api/v3/structures/search", params={"searchKey": "water", "limit": 1}
    ).json()
    structures = data.get("structures") or []
    if not structures:
        pytest.skip("No structures available in this environment")
    return structures[0]["id"]


def test_get_by_ids_returns_requested_attributes(client: Albert, known_structure_id: str):
    """Test that structures are returned with the requested attributes populated."""
    structures = client.structures.get_by_ids(
        structure_ids=[known_structure_id],
        required_fields=[StructureField.ID, StructureField.SMILES],
    )

    assert len(structures) == 1
    assert structures[0].id == known_structure_id
    assert structures[0].smiles


def test_get_by_ids_accepts_unprefixed_ids(client: Albert, known_structure_id: str):
    """Test that IDs without the STT prefix are accepted."""
    bare_id = known_structure_id.removeprefix("STT")

    structures = client.structures.get_by_ids(
        structure_ids=[bare_id], required_fields=[StructureField.SMILES]
    )

    assert len(structures) == 1
    assert structures[0].smiles


def test_get_by_ids_includes_measured_properties(client: Albert, known_structure_id: str):
    """Test that measured property values are included even when not requested."""
    structures = client.structures.get_by_ids(
        structure_ids=[known_structure_id], required_fields=[StructureField.SMILES]
    )

    assert len(structures) == 1
    assert structures[0].molecular_weight is not None
    assert structures[0].molecular_weight.value is not None


def test_get_by_ids_omits_structures_that_do_not_exist(client: Albert, known_structure_id: str):
    """Test that IDs with no matching structure are omitted from the result."""
    structures = client.structures.get_by_ids(
        structure_ids=[known_structure_id, f"STT{uuid.uuid4()}"],
        required_fields=[StructureField.ID],
    )

    assert len(structures) == 1
    assert structures[0].id == known_structure_id


def test_get_by_ids_raises_when_no_ids_match(client: Albert):
    """Test that a lookup where no ID matches raises NotFoundError."""
    with pytest.raises(NotFoundError):
        client.structures.get_by_ids(structure_ids=[f"STT{uuid.uuid4()}"])


def test_get_by_ids_rejects_duplicate_ids(client: Albert, known_structure_id: str):
    """Test that duplicate IDs are rejected."""
    with pytest.raises(BadRequestError):
        client.structures.get_by_ids(structure_ids=[known_structure_id, known_structure_id])


async def test_async_get_by_ids(async_client: AsyncAlbert, known_structure_id: str):
    """Test that the async collection returns structures with the requested attributes."""
    structures = await async_client.structures.get_by_ids(
        structure_ids=[known_structure_id],
        required_fields=[StructureField.ID, StructureField.SMILES],
    )

    assert len(structures) == 1
    assert structures[0].id == known_structure_id
    assert structures[0].smiles
