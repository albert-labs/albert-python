from collections.abc import Iterator
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.lots import Lot, LotAdjustmentAction
from albert.resources.storage_locations import StorageLocation
from tests.seeding import generate_lot_seeds


@pytest.fixture(scope="function")
def seeded_lot(
    client: Albert,
    seeded_inventory,
    seeded_storage_locations,
    seeded_locations,
) -> Iterator[Lot]:
    lot = generate_lot_seeds(
        seeded_inventory=seeded_inventory,
        seeded_storage_locations=seeded_storage_locations,
        seeded_locations=seeded_locations,
    )[0]
    seeded = client.lots.create(lots=[lot])[0]
    yield seeded
    client.lots.delete(id=seeded.id)


def assert_valid_lot_items(returned_list: list[Lot]):
    """Assert all items are valid Lot objects with proper IDs."""
    assert returned_list, "Expected at least one Lot item"
    for c in returned_list[:10]:
        assert isinstance(c, Lot)
        assert isinstance(c.id, str)
        assert c.id.startswith("LOT")


def test_lot_get_all_basic(client: Albert, seeded_lots):
    """Test basic usage of lots.get_all()."""
    results = list(client.lots.get_all(max_items=10))
    assert_valid_lot_items(results)


def test_get_by_id(client: Albert, seeded_lots: list[Lot]):
    got_lot = client.lots.get_by_id(id=seeded_lots[0].id)
    assert got_lot.id == seeded_lots[0].id
    assert got_lot.external_barcode_id == seeded_lots[0].external_barcode_id


def test_get_by_ids(client: Albert, seeded_lots: list[Lot]):
    got_lots = client.lots.get_by_ids(ids=[l.id for l in seeded_lots])
    assert len(got_lots) == len(seeded_lots)
    seeded_ids = [l.id for l in seeded_lots]
    for l in got_lots:
        assert l.id in seeded_ids


def test_update(
    client: Albert, seeded_lot: Lot, seeded_storage_locations: Iterator[list[StorageLocation]]
):
    lot = seeded_lot.model_copy()
    marker = "TEST"
    lot.manufacturer_lot_number = marker
    lot.inventory_on_hand = 10
    current_location_id = lot.storage_location.id if lot.storage_location else None
    new_storage_location = next(
        (sl for sl in seeded_storage_locations if sl.id != current_location_id),
        None,
    )
    assert new_storage_location is not None, (
        "Expected an alternate storage location for update test"
    )
    lot.storage_location = new_storage_location
    updated_lot = client.lots.update(lot=lot)
    assert updated_lot.manufacturer_lot_number == lot.manufacturer_lot_number
    assert updated_lot.inventory_on_hand == 10
    assert updated_lot.storage_location is not None
    assert updated_lot.storage_location.id == new_storage_location.id


def test_adjust_add(client: Albert, seeded_lot: Lot):
    add_quantity = 10.1234567891
    updated_lot = client.lots.adjust(
        lot_id=seeded_lot.id,
        action=LotAdjustmentAction.ADD,
        quantity=add_quantity,
        description="add test",
    )
    assert updated_lot.inventory_on_hand == pytest.approx(
        seeded_lot.inventory_on_hand + add_quantity
    )


def test_adjust_subtract(client: Albert, seeded_lot: Lot):
    subtract_quantity = max(1, seeded_lot.inventory_on_hand / 2)
    updated_lot = client.lots.adjust(
        lot_id=seeded_lot.id,
        action=LotAdjustmentAction.SUBTRACT,
        quantity=subtract_quantity,
        description="subtract test",
    )
    assert updated_lot.inventory_on_hand == pytest.approx(
        seeded_lot.inventory_on_hand - subtract_quantity
    )


def test_adjust_set(client: Albert, seeded_lot: Lot):
    target_quantity = seeded_lot.inventory_on_hand + 7.25
    updated_lot = client.lots.adjust(
        lot_id=seeded_lot.id,
        action=LotAdjustmentAction.SET,
        quantity=target_quantity,
        description="set test",
    )
    assert updated_lot.inventory_on_hand == pytest.approx(target_quantity)


def test_adjust_zero(client: Albert, seeded_lot: Lot):
    updated_lot = client.lots.adjust(
        lot_id=seeded_lot.id,
        action=LotAdjustmentAction.ZERO,
        description="zero test",
    )
    assert updated_lot.inventory_on_hand == pytest.approx(0)


@pytest.mark.parametrize(
    "action, quantity, error_message",
    [
        (LotAdjustmentAction.ZERO, 1, "quantity must be omitted for ZERO action."),
        (
            LotAdjustmentAction.ADD,
            None,
            "quantity must be greater than zero for ADD, SUBTRACT, and SET.",
        ),
        (
            LotAdjustmentAction.SUBTRACT,
            -1,
            "quantity must be greater than zero for ADD, SUBTRACT, and SET.",
        ),
        (
            LotAdjustmentAction.SET,
            0,
            "quantity must be greater than zero for ADD, SUBTRACT, and SET.",
        ),
    ],
)
def test_adjust_validation(client: Albert, seeded_lot: Lot, action, quantity, error_message):
    with pytest.raises(ValueError, match=error_message):
        client.lots.adjust(
            lot_id=seeded_lot.id,
            action=action,
            quantity=quantity,
            description="validation",
        )


def test_transfer_with_explicit_owner(
    client: Albert,
    seeded_lot: Lot,
    seeded_storage_locations: Iterator[list[StorageLocation]],
    static_user,
):
    current_location_id = seeded_lot.storage_location.id if seeded_lot.storage_location else None
    destination = next(
        (sl for sl in seeded_storage_locations if sl.id != current_location_id), None
    )
    assert destination is not None, "Expected an alternate storage location for transfer test"

    transfer_quantity = max(1, seeded_lot.inventory_on_hand / 2)
    split_lot = client.lots.transfer(
        lot_id=seeded_lot.id,
        quantity=transfer_quantity,
        storage_location_id=destination.id,
        owner=static_user.id,
    )
    try:
        assert split_lot.inventory_on_hand == pytest.approx(transfer_quantity)
        assert split_lot.storage_location is not None
        assert split_lot.storage_location.id == destination.id
        assert split_lot.owner is not None
        assert any(o.id == static_user.id for o in split_lot.owner)
    finally:
        with suppress(NotFoundError):
            client.lots.delete(id=split_lot.id)


def test_transfer_defaults_to_current_user(
    client: Albert,
    seeded_lot: Lot,
    seeded_storage_locations: Iterator[list[StorageLocation]],
):
    current_user = client.users.get_current_user()
    current_location_id = seeded_lot.storage_location.id if seeded_lot.storage_location else None
    destination = next(
        (sl for sl in seeded_storage_locations if sl.id != current_location_id), None
    )
    assert destination is not None, "Expected an alternate storage location for transfer test"

    transfer_quantity = max(1, seeded_lot.inventory_on_hand / 2)
    split_lot = client.lots.transfer(
        lot_id=seeded_lot.id,
        quantity=transfer_quantity,
        storage_location_id=destination.id,
    )
    try:
        assert split_lot.owner is not None
        assert any(o.id == current_user.id for o in split_lot.owner)
    finally:
        with suppress(NotFoundError):
            client.lots.delete(id=split_lot.id)


def test_transfer_all_quantity(
    client: Albert,
    seeded_lot: Lot,
    seeded_storage_locations: Iterator[list[StorageLocation]],
):
    current_location_id = seeded_lot.storage_location.id if seeded_lot.storage_location else None
    destination = next(
        (sl for sl in seeded_storage_locations if sl.id != current_location_id), None
    )
    assert destination is not None, "Expected an alternate storage location for transfer test"

    updated_lot = client.lots.transfer(
        lot_id=seeded_lot.id,
        quantity="ALL",
        storage_location_id=destination.id,
    )
    assert updated_lot.id == seeded_lot.id
    assert updated_lot.inventory_on_hand == pytest.approx(seeded_lot.inventory_on_hand)
    assert updated_lot.storage_location is not None
    assert updated_lot.storage_location.id == destination.id
