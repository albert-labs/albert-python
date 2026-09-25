"""Unit tests for AttributeCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_attribute_patch_payload`` (reference
names are add/update only, unit assignment is set-once) with no I/O to fake.
"""

from albert.collections.attributes import AttributeCollection
from albert.core.shared.models.base import EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.resources.attributes import Attribute, AttributeParameterItem, ValidationItem
from albert.resources.parameter_groups import DataType, Operator


def test_unset_reference_name_emits_no_op(offline_session) -> None:
    """Test that an unset reference_name produces no patch operation."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1")  # reference_name never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_none_reference_name_does_not_delete(offline_session) -> None:
    """Test that explicitly clearing reference_name to None emits no op.

    reference_name must remain unique and is add/update only per the update()
    Notes; the builder never emits a delete for it.
    """
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute.model_construct(id="ATR1", reference_name=None)

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_new_reference_name_emits_add_op(offline_session) -> None:
    """Test that setting reference_name where none existed emits an add op."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 25C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "referenceName"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "Viscosity @ 25C"


def test_changed_reference_name_emits_update_op(offline_session) -> None:
    """Test that changing an existing reference_name emits an update op with the old value."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 30C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "referenceName"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "Viscosity @ 25C"
    assert payload.data[0].new_value == "Viscosity @ 30C"


def test_unchanged_reference_name_emits_no_op(offline_session) -> None:
    """Test that setting reference_name to its existing value emits no op."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 25C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_unset_validation_emits_no_op(offline_session) -> None:
    """Test that unset validation produces no patch operation."""
    existing = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1)])
    updated = Attribute(id="ATR1")  # validation never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_changed_validation_emits_full_list_update(offline_session) -> None:
    """Test that changed validation rules emit a whole-list update op."""
    existing = Attribute(
        id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1, max=10)]
    )
    updated = Attribute(
        id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=0, max=10)]
    )

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "validation"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["min"] == 1
    assert payload.data[0].new_value[0]["min"] == 0


def test_unchanged_validation_emits_no_op(offline_session) -> None:
    """Test that equivalent validation rules (new instances, same values) emit no op."""
    existing = Attribute(
        id="ATR1",
        validation=[
            ValidationItem(datatype=DataType.NUMBER, min=1, max=10, operator=Operator.BETWEEN)
        ],
    )
    updated = Attribute(
        id="ATR1",
        validation=[
            ValidationItem(datatype=DataType.NUMBER, min=1, max=10, operator=Operator.BETWEEN)
        ],
    )

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_skip_validation_bypasses_changed_validation(offline_session) -> None:
    """Test that skip_validation=True omits the validation diff even when it changed.

    Used when the caller already applied the change via the enum-specific PUT
    endpoint, to avoid sending the same change twice.
    """
    existing = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1)])
    updated = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=2)])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated, skip_validation=True
    )

    assert payload.data == []


def test_unset_parameters_emits_no_op(offline_session) -> None:
    """Test that unset parameters produce no patch operation."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1")  # parameters never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_changed_parameters_emits_full_list_update(offline_session) -> None:
    """Test that changed parameter setpoints emit a whole-list update op."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="30")])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "parameters"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["value"] == "25"
    assert payload.data[0].new_value[0]["value"] == "30"


def test_unchanged_parameters_emits_no_op(offline_session) -> None:
    """Test that equivalent parameter setpoints emit no op."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_parameters_cleared_to_empty_list_emits_update(offline_session) -> None:
    """Test that clearing parameters to [] is an update (never a silent no-op)."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "parameters"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["value"] == "25"
    assert payload.data[0].new_value == []


def test_unit_id_added_when_no_existing_unit(offline_session) -> None:
    """Test that assigning a unit_id when none is set emits an add op."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", unit_id="UNI1")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "unitId"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "UNI1"


def test_unit_id_ignored_once_a_unit_is_already_assigned(offline_session) -> None:
    """Test that unit_id is set-once: no op is emitted once a unit is assigned."""
    existing = Attribute(id="ATR1", unit=EntityLinkWithName(id="UNI1", name="cP"))
    updated = Attribute(id="ATR1", unit_id="UNI2")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_unset_unit_id_emits_no_op(offline_session) -> None:
    """Test that an unset unit_id produces no patch operation."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1")  # unit_id never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []
