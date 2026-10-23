"""Unit tests for the custom field PATCH payload generator.

Allowed under the patch-builder exception in OPINIONS.md: these guard non-obvious
diff behavior in ``_generate_custom_field_patch_payload`` with no I/O to fake.

Unlike partial-update patch builders, the caller here mutates a single, fully
populated ``CustomField`` (fetched via ``get_by_id``) rather than constructing a
partial object, so the diff is gated on value equality rather than
``model_fields_set``. An unchanged field is one whose value the caller left
identical to the fetched object.
"""

from albert.core.shared.models.patch import PatchOperation
from albert.resources.custom_fields import (
    CustomField,
    EntityCategory,
    FieldType,
    ServiceType,
)
from albert.utils.custom_fields import (
    _generate_custom_entity_category_patches,
    _generate_custom_field_patch_payload,
    _generate_entity_category_patches,
)


def _custom_field(**overrides) -> CustomField:
    defaults = {
        "name": "stage_gate_status",
        "field_type": FieldType.STRING,
        "display_name": "Stage Gate",
        "service": ServiceType.PROJECTS,
    }
    defaults.update(overrides)
    return CustomField(**defaults)


# ---------------------------------------------------------------------------
# Scalar attributes
# ---------------------------------------------------------------------------


def test_unchanged_scalar_emits_no_op():
    """Test that an unchanged scalar attribute emits no patch operation."""
    existing = _custom_field(display_name="Stage Gate")
    updated = _custom_field(display_name="Stage Gate")

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"display_name"}
    )

    assert payload.data == []


def test_scalar_newly_set_emits_add_op():
    """Test that a scalar attribute set from None to a value emits an ADD op."""
    existing = _custom_field(pattern=None)
    updated = _custom_field(pattern="^[A-Z]+$")

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"pattern"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "pattern"
    assert op.operation == PatchOperation.ADD
    assert op.new_value == "^[A-Z]+$"
    assert op.old_value is None


def test_scalar_cleared_emits_delete_op():
    """Test that a scalar attribute set from a value to None emits a DELETE op."""
    existing = _custom_field(pattern="^[A-Z]+$")
    updated = _custom_field(pattern=None)

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"pattern"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "pattern"
    assert op.operation == PatchOperation.DELETE
    assert op.old_value == "^[A-Z]+$"


def test_scalar_changed_emits_update_op_with_old_value():
    """Test that a changed scalar attribute emits an UPDATE op carrying the old value."""
    existing = _custom_field(display_name="Stage Gate")
    updated = _custom_field(display_name="Stage Gate Status")

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"display_name"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "labelName"
    assert op.operation == PatchOperation.UPDATE
    assert op.old_value == "Stage Gate"
    assert op.new_value == "Stage Gate Status"


def test_none_and_empty_container_are_equivalent_and_emit_no_op():
    """Test that None on one side and [] / {} on the other are treated as unchanged."""
    existing = _custom_field(ui_components=None)
    updated = _custom_field(ui_components=[])

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"ui_components"}
    )

    assert payload.data == []

    # And the reverse direction.
    existing = _custom_field(ui_components=[])
    updated = _custom_field(ui_components=None)

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"ui_components"}
    )

    assert payload.data == []


# ---------------------------------------------------------------------------
# Special-cased scalar attributes: UPDATE (not ADD) from unset
# ---------------------------------------------------------------------------


def test_hidden_uses_update_not_add_when_newly_set():
    """Test that 'hidden' uses UPDATE (not ADD) when set from None, per backend contract."""
    existing = _custom_field(hidden=None)
    updated = _custom_field(hidden=True)

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"hidden"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "hidden"
    assert op.operation == PatchOperation.UPDATE
    assert op.new_value is True


def test_searchable_uses_update_not_add_when_newly_set():
    """Test that 'searchable' (alias 'search') uses UPDATE (not ADD) when set from None."""
    existing = _custom_field(searchable=None)
    updated = _custom_field(searchable=True)

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"searchable"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "search"
    assert op.operation == PatchOperation.UPDATE


# ---------------------------------------------------------------------------
# entityCategory / customEntityCategory: item-level add/delete
# ---------------------------------------------------------------------------


def test_entity_categories_both_unset_emits_no_ops():
    """Test that entity_categories left None on both sides emits no operations."""
    existing = _custom_field(entity_categories=None)
    updated = _custom_field(entity_categories=None)

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"entity_categories"}
    )

    assert payload.data == []


def test_entity_categories_newly_added_emits_add_ops():
    """Test that entity_categories set from None emits one ADD op per new category."""
    existing = _custom_field(entity_categories=None)
    updated = _custom_field(entity_categories=[EntityCategory.FORMULAS])

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"entity_categories"}
    )

    assert len(payload.data) == 1
    op = payload.data[0]
    assert op.attribute == "entityCategory"
    assert op.operation == PatchOperation.ADD
    assert op.new_value == EntityCategory.FORMULAS


def test_entity_categories_cleared_to_empty_list_emits_delete_per_item():
    """Test that clearing entity_categories to [] emits a DELETE op per existing item.

    Per the unit-test matrix, an explicit clear to [] is a real diff (a delete of
    each existing entry), never a silent no-op.
    """
    existing = _custom_field(
        entity_categories=[EntityCategory.FORMULAS, EntityCategory.RAW_MATERIALS]
    )
    updated = _custom_field(entity_categories=[])

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"entity_categories"}
    )

    assert len(payload.data) == 2
    assert all(op.operation == PatchOperation.DELETE for op in payload.data)
    assert {op.old_value for op in payload.data} == {
        EntityCategory.FORMULAS,
        EntityCategory.RAW_MATERIALS,
    }


def test_entity_categories_diff_adds_and_removes_distinct_items():
    """Test that entity_categories emits a minimal per-item diff, not a full-list replace."""
    existing = _custom_field(
        entity_categories=[EntityCategory.FORMULAS, EntityCategory.RAW_MATERIALS]
    )
    updated = _custom_field(
        entity_categories=[EntityCategory.RAW_MATERIALS, EntityCategory.EQUIPMENT]
    )

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"entity_categories"}
    )

    ops = {(op.operation, op.old_value or op.new_value) for op in payload.data}
    assert ops == {
        (PatchOperation.DELETE, EntityCategory.FORMULAS),
        (PatchOperation.ADD, EntityCategory.EQUIPMENT),
    }


def test_custom_entity_categories_diff_adds_and_removes_distinct_items():
    """Test that customEntityCategory gets the same item-level diff as entityCategory."""
    existing = _custom_field(custom_entity_categories=["A", "B"])
    updated = _custom_field(custom_entity_categories=["B", "C"])

    payload = _generate_custom_field_patch_payload(
        existing=existing, updated=updated, updatable_attributes={"custom_entity_categories"}
    )

    ops = {(op.operation, op.old_value or op.new_value) for op in payload.data}
    assert ops == {
        (PatchOperation.DELETE, "A"),
        (PatchOperation.ADD, "C"),
    }
    assert all(op.attribute == "customEntityCategory" for op in payload.data)


# ---------------------------------------------------------------------------
# Helper functions directly
# ---------------------------------------------------------------------------


def test_generate_entity_category_patches_none_values_treated_as_empty():
    """Test that None old/new values are treated as empty lists with no diff."""
    assert (
        _generate_entity_category_patches(
            attribute="entityCategory", old_value=None, new_value=None
        )
        == []
    )


def test_generate_entity_category_patches_orders_deletes_before_adds():
    """Test that deletions are emitted before additions in the returned patch list."""
    patches = _generate_entity_category_patches(
        attribute="entityCategory", old_value=["A"], new_value=["B"]
    )

    assert [p.operation for p in patches] == [PatchOperation.DELETE, PatchOperation.ADD]
    assert patches[0].old_value == "A"
    assert patches[1].new_value == "B"


def test_generate_custom_entity_category_patches_delegates_to_entity_category_patches():
    """Test that the custom-entity-category helper produces the same diff shape."""
    patches = _generate_custom_entity_category_patches(
        attribute="customEntityCategory", old_value=["A"], new_value=["B"]
    )

    assert [p.operation for p in patches] == [PatchOperation.DELETE, PatchOperation.ADD]
    assert all(p.attribute == "customEntityCategory" for p in patches)
