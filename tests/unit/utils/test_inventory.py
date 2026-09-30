"""Unit tests for the inventory CAS patch builder.

Allowed under the patch-builder exception in OPINIONS.md: these guard non-obvious
diff behavior in ``_build_cas_patch_operations`` with no I/O to fake.
"""

import pytest

from albert.core.shared.models.base import EntityLink
from albert.resources.cas import Cas
from albert.resources.inventory import CasAmount
from albert.resources.lists import ListItem
from albert.utils.inventory import (
    _build_cas_add_operation,
    _build_cas_delete_operation,
    _build_cas_patch_operations,
    _build_cas_scalar_operation,
    _build_cas_update_operations,
    _build_inventory_function_operations,
    _cas_identifier,
    _ensure_unique_cas_amounts,
    _normalize_inventory_function_ids,
)

# ---------------------------------------------------------------------------
# _cas_identifier
# ---------------------------------------------------------------------------


def test_cas_identifier_prefers_direct_id():
    """Test that a CasAmount.id is preferred over a nested cas.id."""
    amount = CasAmount(min=1.0, max=2.0, id="CAS1")

    assert _cas_identifier(amount) == "CAS1"


def test_cas_identifier_falls_back_to_nested_cas_id():
    """Test that the nested cas.id is used when CasAmount.id is not set.

    ``model_construct`` bypasses the ``set_cas_attributes`` validator (which
    normally copies ``cas.id`` onto ``id``), isolating the fallback branch.
    """
    amount = CasAmount.model_construct(
        min=1.0, max=2.0, id=None, cas=Cas(id="CAS2", number="123-45-6")
    )

    assert _cas_identifier(amount) == "CAS2"


def test_cas_identifier_raises_without_any_identifier():
    """Test that a CasAmount with neither id nor cas raises ValueError."""
    amount = CasAmount.model_construct(min=1.0, max=2.0, id=None, cas=None)

    with pytest.raises(ValueError, match="identifier"):
        _cas_identifier(amount)


# ---------------------------------------------------------------------------
# _ensure_unique_cas_amounts
# ---------------------------------------------------------------------------


def test_ensure_unique_cas_amounts_passes_for_distinct_ids():
    """Test that distinct CAS identifiers do not raise."""
    amounts = [CasAmount(min=1.0, max=2.0, id="CAS1"), CasAmount(min=1.0, max=2.0, id="CAS2")]

    _ensure_unique_cas_amounts(amounts)


def test_ensure_unique_cas_amounts_raises_on_duplicate_id():
    """Test that a duplicate CAS identifier raises ValueError."""
    amounts = [CasAmount(min=1.0, max=2.0, id="CAS1"), CasAmount(min=3.0, max=4.0, id="CAS1")]

    with pytest.raises(ValueError, match="duplicate CAS"):
        _ensure_unique_cas_amounts(amounts)


# ---------------------------------------------------------------------------
# _build_cas_add_operation
# ---------------------------------------------------------------------------


def test_build_cas_add_operation_includes_required_min_max_and_identifier():
    """Test that an add operation always carries the identifier and min/max."""
    amount = CasAmount(min=1.0, max=2.0, id="CAS1")

    operation = _build_cas_add_operation(amount)

    assert operation == {
        "operation": "add",
        "attribute": "casId",
        "newValue": "CAS1",
        "min": 1.0,
        "max": 2.0,
    }


def test_build_cas_add_operation_includes_optional_fields_when_set():
    """Test that casCategory, type, and classificationType are added when set."""
    amount = CasAmount(
        min=1.0,
        max=2.0,
        id="CAS1",
        cas_category="TradeSecret",
        type="component",
        classification_type="REACH",
    )

    operation = _build_cas_add_operation(amount)

    assert operation["casCategory"] == "TradeSecret"
    assert operation["type"] == "component"
    assert operation["classificationType"] == "REACH"


def test_build_cas_add_operation_omits_optional_fields_when_unset():
    """Test that casCategory, type, and classificationType are absent when unset."""
    amount = CasAmount(min=1.0, max=2.0, id="CAS1")

    operation = _build_cas_add_operation(amount)

    assert "casCategory" not in operation
    assert "type" not in operation
    assert "classificationType" not in operation


@pytest.mark.parametrize(
    "kwargs,expect_substance_id",
    [
        pytest.param({}, False, id="unset"),
        pytest.param({"substance_id": None}, False, id="explicit-none"),
        pytest.param({"substance_id": ""}, False, id="explicit-empty-string"),
        pytest.param({"substance_id": "SUB1"}, True, id="explicit-value"),
    ],
)
def test_build_cas_add_operation_substance_id_requires_set_and_truthy(kwargs, expect_substance_id):
    """Test that substanceId is only added when explicitly set to a truthy value."""
    amount = CasAmount(min=1.0, max=2.0, id="CAS1", **kwargs)

    operation = _build_cas_add_operation(amount)

    assert ("substanceId" in operation) == expect_substance_id
    if expect_substance_id:
        assert operation["substanceId"] == "SUB1"


# ---------------------------------------------------------------------------
# _build_cas_delete_operation
# ---------------------------------------------------------------------------


def test_build_cas_delete_operation():
    """Test that a delete operation only carries the casId attribute and oldValue."""
    operation = _build_cas_delete_operation("CAS1")

    assert operation == {
        "operation": "delete",
        "attribute": "casId",
        "oldValue": "CAS1",
    }


# ---------------------------------------------------------------------------
# _normalize_inventory_function_ids
# ---------------------------------------------------------------------------


def test_normalize_inventory_function_ids_none_returns_empty_list():
    """Test that a None inventory_function value normalizes to an empty list."""
    assert _normalize_inventory_function_ids(None) == []


def test_normalize_inventory_function_ids_empty_list_returns_empty_list():
    """Test that an empty inventory_function value normalizes to an empty list."""
    assert _normalize_inventory_function_ids([]) == []


def test_normalize_inventory_function_ids_handles_mixed_types():
    """Test that str, BaseResource, and EntityLink entries all yield their id."""
    value = [
        "LST1",
        ListItem(id="LST2", name="Function 2"),
        EntityLink(id="LST3"),
    ]

    assert _normalize_inventory_function_ids(value) == ["LST1", "LST2", "LST3"]


def test_normalize_inventory_function_ids_filters_falsy_entries():
    """Test that empty strings and BaseResource entries without an id are dropped."""
    value = [
        "",
        ListItem(name="No id"),
        EntityLink(id="LST1"),
    ]

    assert _normalize_inventory_function_ids(value) == ["LST1"]


def test_normalize_inventory_function_ids_ignores_unsupported_types():
    """Test that entries which are neither str, BaseResource, nor EntityLink are skipped."""
    value = ["LST1", 42, None]

    assert _normalize_inventory_function_ids(value) == ["LST1"]


# ---------------------------------------------------------------------------
# _build_inventory_function_operations
# ---------------------------------------------------------------------------


def test_build_inventory_function_operations_add_and_delete():
    """Test that added and removed function ids each emit their own operation."""
    operations = _build_inventory_function_operations(
        entity_id="CAS1",
        existing=["LST1", "LST2"],
        updated=["LST2", "LST3"],
    )

    assert operations == [
        {
            "attribute": "inventoryFunction",
            "entityId": "CAS1",
            "operation": "add",
            "newValue": ["LST3"],
        },
        {
            "attribute": "inventoryFunction",
            "entityId": "CAS1",
            "operation": "delete",
            "oldValue": ["LST1"],
        },
    ]


def test_build_inventory_function_operations_no_diff_returns_empty_list():
    """Test that identical existing and updated function ids emit no operations."""
    operations = _build_inventory_function_operations(
        entity_id="CAS1",
        existing=["LST1"],
        updated=["LST1"],
    )

    assert operations == []


# ---------------------------------------------------------------------------
# _build_cas_scalar_operation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "old_value,new_value,expected",
    [
        pytest.param(5.0, 5.0, None, id="unchanged"),
        pytest.param(None, None, None, id="both-none"),
        pytest.param(
            5.0,
            None,
            {
                "attribute": "inventoryValue",
                "entityId": "CAS1",
                "operation": "delete",
                "oldValue": 5.0,
            },
            id="cleared",
        ),
        pytest.param(
            None,
            10.0,
            {
                "attribute": "inventoryValue",
                "entityId": "CAS1",
                "operation": "add",
                "newValue": 10.0,
            },
            id="newly-set",
        ),
        pytest.param(
            5.0,
            10.0,
            {
                "attribute": "inventoryValue",
                "entityId": "CAS1",
                "operation": "update",
                "oldValue": 5.0,
                "newValue": 10.0,
            },
            id="changed",
        ),
    ],
)
def test_build_cas_scalar_operation_matrix(old_value, new_value, expected):
    """Test the add/update/delete/no-op matrix for a single scalar CAS attribute."""
    operation = _build_cas_scalar_operation(
        attribute="inventoryValue", entity_id="CAS1", old_value=old_value, new_value=new_value
    )

    assert operation == expected


# ---------------------------------------------------------------------------
# _build_cas_update_operations
# ---------------------------------------------------------------------------


def test_build_cas_update_operations_no_op_when_nothing_changed():
    """Test that an update with all fields unchanged emits no operations."""
    existing = CasAmount(min=1.0, max=2.0, id="CAS1", target=5.0, cas_category="TradeSecret")
    updated = CasAmount(min=1.0, max=2.0, id="CAS1", target=5.0, cas_category="TradeSecret")

    assert _build_cas_update_operations(existing, updated) == []


def test_build_cas_update_operations_required_fields_diffed_when_changed():
    """Test that min/max are diffed as update ops since they are always set."""
    existing = CasAmount(min=1.0, max=2.0, id="CAS1")
    updated = CasAmount(min=1.5, max=2.0, id="CAS1")

    operations = _build_cas_update_operations(existing, updated)

    assert operations == [
        {
            "attribute": "min",
            "entityId": "CAS1",
            "operation": "update",
            "oldValue": 1.0,
            "newValue": 1.5,
        }
    ]


def test_build_cas_update_operations_optional_field_unset_on_updated_is_no_op():
    """Test that an optional scalar field left unset on ``updated`` is left untouched.

    Even though ``existing`` has a target value, omitting ``target`` from the
    caller-built ``updated`` object must not emit a delete operation.
    """
    existing = CasAmount(min=1.0, max=2.0, id="CAS1", target=5.0)
    updated = CasAmount(min=1.0, max=2.0, id="CAS1")

    operations = _build_cas_update_operations(existing, updated)

    assert operations == []


def test_build_cas_update_operations_optional_field_explicit_change():
    """Test that an explicitly-changed optional scalar field emits an update op."""
    existing = CasAmount(min=1.0, max=2.0, id="CAS1", cas_category="TradeSecret")
    updated = CasAmount(min=1.0, max=2.0, id="CAS1", cas_category="Public")

    operations = _build_cas_update_operations(existing, updated)

    assert operations == [
        {
            "attribute": "casCategory",
            "entityId": "CAS1",
            "operation": "update",
            "oldValue": "TradeSecret",
            "newValue": "Public",
        }
    ]


def test_build_cas_update_operations_inventory_function_only_emitted_when_set():
    """Test that inventory_function is diffed only when explicitly set on updated."""
    existing = CasAmount(min=1.0, max=2.0, id="CAS1", inventory_function=["LST1"])
    unset_updated = CasAmount(min=1.0, max=2.0, id="CAS1")

    assert _build_cas_update_operations(existing, unset_updated) == []

    set_updated = CasAmount(min=1.0, max=2.0, id="CAS1", inventory_function=["LST2"])
    operations = _build_cas_update_operations(existing, set_updated)

    assert operations == [
        {
            "attribute": "inventoryFunction",
            "entityId": "CAS1",
            "operation": "add",
            "newValue": ["LST2"],
        },
        {
            "attribute": "inventoryFunction",
            "entityId": "CAS1",
            "operation": "delete",
            "oldValue": ["LST1"],
        },
    ]


def test_build_cas_update_operations_never_emits_substance_id_op():
    """Test that a changed substance_id is never diffed by the update builder.

    Regression guard for OPINIONS.md: substanceId is set on add, preserved on
    min/max update, and removed only when the whole CAS entry is deleted, never
    via a standalone substanceId update/delete operation.
    """
    existing = CasAmount(min=1.0, max=2.0, id="CAS1", substance_id="SUB1")
    updated = CasAmount(min=1.5, max=2.0, id="CAS1", substance_id="SUB2")

    operations = _build_cas_update_operations(existing, updated)

    assert all(op["attribute"] != "substanceId" for op in operations)


# ---------------------------------------------------------------------------
# _build_cas_patch_operations
# ---------------------------------------------------------------------------


def test_build_cas_patch_operations_empty_inputs_return_empty_list():
    """Test that no existing and no updated CAS amounts produce no operations."""
    assert _build_cas_patch_operations(existing=None, updated=None) == []


def test_build_cas_patch_operations_add_new_cas():
    """Test that a CAS present only in updated emits an add operation."""
    operations = _build_cas_patch_operations(
        existing=[],
        updated=[CasAmount(min=1.0, max=2.0, id="CAS1")],
    )

    assert operations == [
        {
            "operation": "add",
            "attribute": "casId",
            "newValue": "CAS1",
            "min": 1.0,
            "max": 2.0,
        }
    ]


def test_build_cas_patch_operations_add_new_cas_with_target_and_category():
    """Test that a newly added CAS also emits inventoryValue/casCategory add ops."""
    operations = _build_cas_patch_operations(
        existing=[],
        updated=[CasAmount(min=1.0, max=2.0, id="CAS1", target=5.0, cas_category="TradeSecret")],
    )

    assert {
        "attribute": "inventoryValue",
        "entityId": "CAS1",
        "operation": "add",
        "newValue": 5.0,
    } in (operations)
    assert {
        "attribute": "casCategory",
        "entityId": "CAS1",
        "operation": "add",
        "newValue": "TradeSecret",
    } in operations


def test_build_cas_patch_operations_add_new_cas_with_inventory_function():
    """Test that a newly added CAS with inventory_function also emits an add op for it."""
    operations = _build_cas_patch_operations(
        existing=[],
        updated=[CasAmount(min=1.0, max=2.0, id="CAS1", inventory_function=["LST1"])],
    )

    assert {
        "attribute": "inventoryFunction",
        "entityId": "CAS1",
        "operation": "add",
        "newValue": ["LST1"],
    } in operations


def test_build_cas_patch_operations_delete_removed_cas():
    """Test that a CAS present only in existing emits a delete operation."""
    operations = _build_cas_patch_operations(
        existing=[CasAmount(min=1.0, max=2.0, id="CAS1")],
        updated=[],
    )

    assert operations == [
        {
            "operation": "delete",
            "attribute": "casId",
            "oldValue": "CAS1",
        }
    ]


def test_build_cas_patch_operations_delete_never_includes_substance_id():
    """Test that removing a CAS with a substance_id never emits a substanceId op.

    Regression guard: substanceId is only removed implicitly, by deleting the
    whole CAS entry via casId, never as its own delete operation.
    """
    operations = _build_cas_patch_operations(
        existing=[CasAmount(min=1.0, max=2.0, id="CAS1", substance_id="SUB1")],
        updated=[],
    )

    assert operations == [
        {
            "operation": "delete",
            "attribute": "casId",
            "oldValue": "CAS1",
        }
    ]
    assert all(op["attribute"] != "substanceId" for op in operations)


def test_build_cas_patch_operations_update_existing_cas():
    """Test that a CAS present in both is diffed via the update path."""
    operations = _build_cas_patch_operations(
        existing=[CasAmount(min=1.0, max=2.0, id="CAS1")],
        updated=[CasAmount(min=1.5, max=2.0, id="CAS1")],
    )

    assert operations == [
        {
            "attribute": "min",
            "entityId": "CAS1",
            "operation": "update",
            "oldValue": 1.0,
            "newValue": 1.5,
        }
    ]


def test_build_cas_patch_operations_unchanged_cas_emits_no_operations():
    """Test that a CAS with identical existing and updated values emits nothing."""
    operations = _build_cas_patch_operations(
        existing=[CasAmount(min=1.0, max=2.0, id="CAS1")],
        updated=[CasAmount(min=1.0, max=2.0, id="CAS1")],
    )

    assert operations == []


def test_build_cas_patch_operations_raises_on_duplicate_updated_cas():
    """Test that duplicate CAS identifiers in updated raise before any diffing."""
    with pytest.raises(ValueError, match="duplicate CAS"):
        _build_cas_patch_operations(
            existing=[],
            updated=[
                CasAmount(min=1.0, max=2.0, id="CAS1"),
                CasAmount(min=3.0, max=4.0, id="CAS1"),
            ],
        )
