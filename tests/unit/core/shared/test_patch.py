from albert.collections.lots import LotCollection
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.lots import Lot


def test_exclude_unset_default():
    payload = PatchPayload(
        data=[
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
                old_value=None,
            ),
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
            ),
        ]
    )
    dumped = payload.model_dump(mode="json", by_alias=True)

    datum0 = dumped["data"][0]
    assert datum0["oldValue"] is None
    assert datum0["newValue"] == 4

    datum1 = dumped["data"][1]
    assert "oldValue" not in datum1
    assert datum1["newValue"] == 4


def test_lots_patch_payload_stringifies_numeric_values():
    """Test that lot cost and initialQuantity patch values are serialized as decimal strings."""
    existing = Lot(
        id="LOT1",
        inventory_id="INV1",
        inventory_on_hand=10.0,
        cost=50.0,
        initial_quantity=100.0,
    )
    updated = existing.model_copy(update={"cost": 42.5, "initial_quantity": 200.0})

    payload = LotCollection(session=None)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )
    by_attribute = {d.attribute: d for d in payload.data}

    assert by_attribute["cost"].operation == PatchOperation.UPDATE
    assert by_attribute["cost"].old_value == "50"
    assert by_attribute["cost"].new_value == "42.5"
    assert by_attribute["initialQuantity"].operation == PatchOperation.UPDATE
    assert by_attribute["initialQuantity"].old_value == "100"
    assert by_attribute["initialQuantity"].new_value == "200"
