from types import SimpleNamespace

import pytest

from albert.core.shared.models.base import EntityLink
from albert.resources.inventory import InventoryCategory, InventoryDensity
from albert.resources.lots import Lot, LotVolumeUnit


def test_lot_volume_coercion_and_serialization():
    lot = Lot(
        inventory_id="INVA123",
        storage_location=EntityLink(id="STL123"),
        initial_quantity=100.0,
        inventory_on_hand=100.0,
        initial_quantity_l=127.39,
        entry_unit=LotVolumeUnit.LITER,
        cost=80.0,
        cost_l=62.8,
        density="0.785",
    )
    assert isinstance(lot.density, InventoryDensity)
    assert lot.density.value == pytest.approx(0.785)
    assert lot.entry_unit == LotVolumeUnit.LITER

    dumped = lot.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["density"] == "0.785"
    assert dumped["initialQuantityL"] == "127.39"
    assert dumped["costL"] == "62.8"
    assert dumped["entryUnit"] == "L"


@pytest.mark.parametrize("density_value", [0.785, "0.785"])
def test_lot_density_coerces_int_float_and_str(density_value):
    """Test that density accepts a bare int, float, or string and wraps it in InventoryDensity."""
    lot = Lot(inventory_id="INVA123", inventory_on_hand=1.0, density=density_value)

    assert isinstance(lot.density, InventoryDensity)
    assert lot.density.value == pytest.approx(0.785)


def test_lot_density_object_passes_through():
    """Test that an existing InventoryDensity object is kept as-is."""
    density = InventoryDensity(value=1.5)
    lot = Lot(inventory_id="INVA123", inventory_on_hand=1.0, density=density)

    assert lot.density is density


@pytest.mark.parametrize(
    ("field", "alias", "raw", "expected"),
    [
        ("has_notes", "hasNotes", "1", True),
        ("has_notes", "hasNotes", "0", False),
        ("has_notes", "hasNotes", True, True),
        ("has_attachments", "hasAttachments", "1", True),
        ("has_attachments", "hasAttachments", "0", False),
        ("has_attachments", "hasAttachments", False, False),
    ],
)
def test_lot_has_notes_and_has_attachments_coerce_string_flags(field, alias, raw, expected):
    """Test that has_notes/has_attachments coerce '1'/'0' strings and pass through booleans."""
    lot = Lot(inventory_id="INVA123", inventory_on_hand=1.0, **{alias: raw})

    assert getattr(lot, field) is expected


def test_lot_workflow_id_kept_when_already_set():
    """Test that an explicit workflowId is not overridden by the Workflows list."""
    lot = Lot(
        inventory_id="INVA123",
        inventory_on_hand=1.0,
        workflowId="WFLX",
        Workflows=[{"id": "WFL5", "category": "FINAL"}],
    )

    assert lot.workflow_id == "WFLX"


def test_lot_workflow_id_prefers_final_category():
    """Test that workflow_id is populated from the FINAL-category workflow when present."""
    lot = Lot(
        inventory_id="INVA123",
        inventory_on_hand=1.0,
        Workflows=[{"id": "WFL1", "category": "DRAFT"}, {"id": "WFL2", "category": "FINAL"}],
    )

    assert lot.workflow_id == "WFL2"


def test_lot_workflow_id_falls_back_to_first_when_no_final():
    """Test that workflow_id falls back to the first workflow when none is FINAL."""
    lot = Lot(
        inventory_id="INVA123",
        inventory_on_hand=1.0,
        Workflows=[{"id": "WFL3", "category": "DRAFT"}, {"id": "WFL4", "category": "DRAFT"}],
    )

    assert lot.workflow_id == "WFL3"


def test_lot_workflow_id_stays_none_without_workflows():
    """Test that workflow_id remains unset when no workflowId or Workflows are supplied."""
    lot = Lot(inventory_id="INVA123", inventory_on_hand=1.0)

    assert lot.workflow_id is None


def test_lot_workflow_population_is_a_noop_for_non_dict_input():
    """Test that populate_workflow_id_from_workflows passes through non-dict input untouched."""
    obj = SimpleNamespace(parentId="INVA123", inventoryOnHand=5.0, workflowId=None, Workflows=None)

    lot = Lot.model_validate(obj, from_attributes=True)

    assert lot.workflow_id is None
    assert lot.inventory_id == "INVA123"


def test_lot_numeric_serializers_strip_trailing_zeros():
    """Test that initial_quantity, cost, and inventory_on_hand serialize as trimmed decimal strings."""
    lot = Lot(
        inventory_id="INVA123",
        storage_location=EntityLink(id="STL123"),
        initial_quantity=100.0,
        inventory_on_hand=100.0,
        cost=80.0,
    )

    dumped = lot.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["initialQuantity"] == "100"
    assert dumped["cost"] == "80"
    assert dumped["inventoryOnHand"] == "100"


def test_lot_optional_numeric_serializers_omit_none_values():
    """Test that initial_quantity_l, cost_l, and density serialize to None (and are dropped) when unset."""
    lot = Lot(inventory_id="INVA123", inventory_on_hand=5.5)

    dumped = lot.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert "initialQuantityL" not in dumped
    assert "costL" not in dumped
    assert "density" not in dumped
    assert dumped["inventoryOnHand"] == "5.5"


def test_lot_numeric_serializer_leaves_non_decimal_formatting_untouched():
    """Test that a value with no fractional part in its formatted form is not trimmed further."""
    lot = Lot(inventory_id="INVA123", inventory_on_hand=1.0, cost=float("inf"))

    dumped = lot.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["cost"] == "inf"

    round_tripped = Lot.model_validate(dumped)
    assert round_tripped.cost == float("inf")


def test_lot_parent_category_alias():
    """Test that parent_category parses from the parentIdCategory response field."""
    lot = Lot(
        albertId="LOT1",
        parentId="INV1",
        inventoryOnHand=10.0,
        parentIdCategory="RawMaterials",
    )
    assert lot.parent_category == InventoryCategory.RAW_MATERIALS
