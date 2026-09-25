from albert.collections.lots import LotCollection
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.lots import Lot
from albert.resources.parameter_groups import ParameterGroup, ParameterValue
from albert.utils._patch import generate_parameter_group_patches


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


def test_parameter_group_row_delete_uses_parameters_attribute():
    """Test that deleting a parameter group row emits the ``parameters`` attribute."""
    existing = ParameterGroup(
        name="Mixing Step",
        parameters=[
            ParameterValue(id="PRM123", value="500", sequence="ROW1"),
            ParameterValue(id="PRM456", value="600", sequence="ROW2"),
        ],
    )
    updated = ParameterGroup(
        name="Mixing Step",
        parameters=[ParameterValue(id="PRM123", value="500", sequence="ROW1")],
    )

    general_patches, _, _ = generate_parameter_group_patches(
        initial_patches=PatchPayload(data=[]),
        updated_parameter_group=updated,
        existing_parameter_group=existing,
    )
    dumped = general_patches.model_dump(mode="json", by_alias=True, exclude_none=True)

    deletes = [d for d in dumped["data"] if d["operation"] == "delete"]
    assert len(deletes) == 1
    assert deletes[0]["attribute"] == "parameters"
    assert deletes[0]["oldValue"] == ["ROW2"]
