"""Unit tests for LotCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_lots_patch_payload`` (inventory_on_hand
is patched as a delta, cost_l always uses update, storage_location/owner are
flattened to bare ids, workflow_id is update-only) with no I/O to fake.
"""

import pytest

from albert.collections.lots import LotCollection
from albert.core.shared.models.base import EntityLink
from albert.core.shared.models.patch import PatchOperation
from albert.resources.lots import Lot


def _lot(**kwargs) -> Lot:
    defaults = {"id": "LOT1", "inventory_id": "INVA1", "inventory_on_hand": 5.0}
    defaults.update(kwargs)
    return Lot(**defaults)


# --- inventory_on_hand delta special case ---


def test_inventory_on_hand_increase_emits_positive_delta(offline_session) -> None:
    """Test that increasing inventory_on_hand emits an update op carrying the positive delta."""
    existing = _lot(inventory_on_hand=5.0)
    updated = _lot(inventory_on_hand=8.0)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "inventoryOnHand"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].new_value == "3.00000000000000"
    assert ops[0].old_value == "5.0"


def test_inventory_on_hand_decrease_emits_negative_delta(offline_session) -> None:
    """Test that decreasing inventory_on_hand emits an update op carrying a negative delta."""
    existing = _lot(inventory_on_hand=5.0)
    updated = _lot(inventory_on_hand=3.0)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "inventoryOnHand"]
    assert len(ops) == 1
    assert ops[0].new_value == "-2.00000000000000"


def test_inventory_on_hand_unchanged_emits_no_op(offline_session) -> None:
    """Test that an unchanged inventory_on_hand emits no patch operation."""
    existing = _lot(inventory_on_hand=5.0)
    updated = _lot(inventory_on_hand=5.0)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "inventoryOnHand"] == []


# --- cost_l always emits update ---


def test_cost_l_unset_emits_no_op(offline_session) -> None:
    """Test that an unset cost_l produces no patch operation."""
    existing = _lot(cost_l=5.0)
    updated = _lot()  # cost_l never set

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "costL"] == []


def test_cost_l_added_emits_update_with_zero_old_value(offline_session) -> None:
    """Test that setting cost_l for the first time still uses update, with old_value '0'."""
    existing = _lot()  # cost_l unset -> None
    updated = _lot(cost_l=62.8)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "costL"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "0"
    assert ops[0].new_value == "62.8"


def test_cost_l_changed_emits_update_with_formatted_values(offline_session) -> None:
    """Test that a changed cost_l emits an update op with decimal-formatted old and new values."""
    existing = _lot(cost_l=50.0)
    updated = _lot(cost_l=62.8)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "costL"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "50"
    assert ops[0].new_value == "62.8"


def test_cost_l_cleared_still_uses_update_operation(offline_session) -> None:
    """Test that clearing cost_l to None still emits an update op (not a delete).

    The backend requires costL changes to always be sent as "update", per the
    comment in _generate_lots_patch_payload.
    """
    existing = _lot(cost_l=50.0)
    updated = _lot(cost_l=None)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "costL"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "50"
    assert ops[0].new_value is None


# --- storage_location flattened to bare ids ---


def test_storage_location_unset_emits_no_op(offline_session) -> None:
    """Test that an unset storage_location produces no patch operation."""
    existing = _lot(storage_location=EntityLink(id="STL1"))
    updated = _lot()  # storage_location never set

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "storageLocation"] == []


def test_storage_location_added_emits_add_with_bare_id(offline_session) -> None:
    """Test that assigning a storage_location for the first time emits an add op with a bare id."""
    existing = _lot()  # storage_location unset -> None
    updated = _lot(storage_location=EntityLink(id="STL1"))

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "storageLocation"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.ADD
    assert ops[0].new_value == "STL1"
    assert ops[0].old_value is None


def test_storage_location_changed_emits_update_with_bare_ids(offline_session) -> None:
    """Test that changing storage_location emits an update op with bare old/new ids."""
    existing = _lot(storage_location=EntityLink(id="STL1"))
    updated = _lot(storage_location=EntityLink(id="STL2"))

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "storageLocation"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "STL1"
    assert ops[0].new_value == "STL2"


def test_storage_location_cleared_emits_delete_with_bare_old_id(offline_session) -> None:
    """Test that clearing storage_location emits a delete op with the bare old id."""
    existing = _lot(storage_location=EntityLink(id="STL1"))
    updated = _lot(storage_location=None)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "storageLocation"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.DELETE
    assert ops[0].old_value == "STL1"
    assert ops[0].new_value is None


def test_storage_location_unchanged_emits_no_op(offline_session) -> None:
    """Test that an unchanged storage_location emits no patch operation."""
    existing = _lot(storage_location=EntityLink(id="STL1"))
    updated = _lot(storage_location=EntityLink(id="STL1"))

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "storageLocation"] == []


# --- owner: single-owner list flattened to a bare id ---


def test_owner_unset_emits_no_op(offline_session) -> None:
    """Test that an unset owner produces no patch operation."""
    existing = _lot(owner=[EntityLink(id="USR1")])
    updated = _lot()  # owner never set

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "Owner"] == []


def test_owner_added_emits_add_with_bare_id(offline_session) -> None:
    """Test that assigning an owner for the first time emits an add op with a bare id."""
    existing = _lot()  # owner unset -> None
    updated = _lot(owner=[EntityLink(id="USR1")])

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "Owner"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.ADD
    assert ops[0].new_value == "USR1"
    assert ops[0].old_value is None


def test_owner_changed_emits_update_with_bare_ids(offline_session) -> None:
    """Test that reassigning the owner emits an update op with bare old/new ids."""
    existing = _lot(owner=[EntityLink(id="USR1")])
    updated = _lot(owner=[EntityLink(id="USR2")])

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "Owner"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "USR1"
    assert ops[0].new_value == "USR2"


def test_owner_unchanged_emits_no_op(offline_session) -> None:
    """Test that assigning the same single owner emits no patch operation."""
    existing = _lot(owner=[EntityLink(id="USR1")])
    updated = _lot(owner=[EntityLink(id="USR1")])

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "Owner"] == []


def test_owner_with_more_than_one_entry_raises(offline_session) -> None:
    """Test that assigning more than one owner raises: a lot can only have one owner."""
    existing = _lot(owner=[EntityLink(id="USR1")])
    updated = _lot(owner=[EntityLink(id="USR1"), EntityLink(id="USR2")])

    with pytest.raises(ValueError, match="A lot can only have one owner"):
        LotCollection(session=offline_session)._generate_lots_patch_payload(
            existing=existing, updated=updated
        )


# --- workflow_id: update-only (ADD is rewritten to UPDATE, dropping old_value) ---


def test_workflow_id_first_assignment_rewrites_add_to_update(offline_session) -> None:
    """Test that assigning workflow_id for the first time is rewritten from add to update."""
    existing = _lot()  # workflow_id unset -> None
    updated = _lot(workflow_id="WFL1")

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "workflowId"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].new_value == "WFL1"
    assert ops[0].old_value is None


def test_workflow_id_changed_keeps_update_with_old_value(offline_session) -> None:
    """Test that changing an existing workflow_id stays an update op with the old value."""
    existing = _lot(workflow_id="WFL1")
    updated = _lot(workflow_id="WFL2")

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "workflowId"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "WFL1"
    assert ops[0].new_value == "WFL2"


def test_workflow_id_cleared_emits_delete(offline_session) -> None:
    """Test that clearing workflow_id emits a delete op (not rewritten, since it isn't an add)."""
    existing = _lot(workflow_id="WFL1")
    updated = _lot(workflow_id=None)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "workflowId"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.DELETE
    assert ops[0].old_value == "WFL1"


def test_workflow_id_unset_emits_no_op(offline_session) -> None:
    """Test that an unset workflow_id produces no patch operation."""
    existing = _lot(workflow_id="WFL1")
    updated = _lot()  # workflow_id never set

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert [d for d in payload.data if d.attribute == "workflowId"] == []


# --- an ordinary attribute is unaffected by the special-case post-processing ---


def test_ordinary_scalar_attribute_changed_emits_plain_update(offline_session) -> None:
    """Test that a non-special attribute (manufacturer_lot_number) still diffs normally."""
    existing = _lot(manufacturer_lot_number="MLN-1")
    updated = _lot(manufacturer_lot_number="MLN-2")

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    ops = [d for d in payload.data if d.attribute == "manufacturerLotNumber"]
    assert len(ops) == 1
    assert ops[0].operation == PatchOperation.UPDATE
    assert ops[0].old_value == "MLN-1"
    assert ops[0].new_value == "MLN-2"
