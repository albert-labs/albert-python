"""Unit tests for EntityTypeCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_special_attribute_patches`` (nested
nested-field add-vs-update, whole-list custom_fields diffing) with no I/O to
fake.
"""

import responses

from albert.collections.entity_types import EntityTypeCollection
from albert.core.shared.models.patch import PatchOperation
from albert.resources.entity_types import (
    EntityCategory,
    EntityCustomField,
    EntityServiceType,
    EntityType,
    EntityTypeSearchQueryStrings,
    EntityTypeStandardFieldRequired,
    EntityTypeStandardFieldVisibility,
    FieldSection,
)
from tests.unit.conftest import UNIT_BASE_URL


def _entity_type(**kwargs) -> EntityType:
    return EntityType(
        id="ETT1",
        label="Stability Task",
        service=EntityServiceType.TASKS,
        category=EntityCategory.PROPERTY,
        **kwargs,
    )


def test_unset_custom_fields_emits_no_patches(offline_session) -> None:
    """Test that unset custom_fields on both sides emits no patches."""
    existing = _entity_type()
    updated = _entity_type()

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert patches == []


def test_new_custom_fields_emits_add_op(offline_session) -> None:
    """Test that setting custom_fields where none existed emits an add op."""
    existing = _entity_type()
    updated = _entity_type(
        custom_fields=[
            EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=False),
        ]
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert len(patches) == 1
    assert patches[0].attribute == "customFields"
    assert patches[0].operation == PatchOperation.ADD
    assert patches[0].new_value == [{"id": "CTF1", "section": "top", "hidden": False}]


def test_changed_custom_fields_emits_update_op(offline_session) -> None:
    """Test that changed custom_fields content emits an update op with old and new dumps."""
    existing = _entity_type(
        custom_fields=[EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=False)]
    )
    updated = _entity_type(
        custom_fields=[EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=True)]
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert len(patches) == 1
    assert patches[0].attribute == "customFields"
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].old_value == [{"id": "CTF1", "section": "top", "hidden": False}]
    assert patches[0].new_value == [{"id": "CTF1", "section": "top", "hidden": True}]


def test_unchanged_custom_fields_emits_no_op(offline_session) -> None:
    """Test that identical custom_fields content emits no patch operation."""
    existing = _entity_type(
        custom_fields=[EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=False)]
    )
    updated = _entity_type(
        custom_fields=[EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=False)]
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert patches == []


@responses.activate
def test_update_with_no_changes_sends_no_patch(offline_session) -> None:
    """Test that updating an entity type with unchanged custom_fields sends no PATCH."""
    custom_fields = [EntityCustomField(id="CTF1", section=FieldSection.TOP, hidden=False)]
    current = _entity_type(custom_fields=custom_fields)
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/entitytypes/ETT1",
        json=current.model_dump(by_alias=True, mode="json", exclude_none=True),
    )

    result = EntityTypeCollection(session=offline_session).update(
        entity_type=_entity_type(custom_fields=custom_fields)
    )

    assert result.id == "ETT1"
    assert [c.request.method for c in responses.calls] == ["GET"]


def test_unset_standard_field_visibility_emits_no_patches(offline_session) -> None:
    """Test that an unset standard_field_visibility emits no patches for its sub-fields."""
    existing = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=True, due_date=False
        )
    )
    updated = _entity_type()  # standard_field_visibility never set

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert patches == []


def test_new_standard_field_visibility_emits_add_per_changed_field(offline_session) -> None:
    """Test that a first-time standard_field_visibility emits add ops (no existing value)."""
    existing = _entity_type()
    updated = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=False, due_date=False
        )
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    by_attribute = {p.attribute: p for p in patches}
    assert set(by_attribute) == {
        "standardFieldVisibility.Notes",
        "standardFieldVisibility.Tags",
        "standardFieldVisibility.DueDate",
    }
    assert all(p.operation == PatchOperation.ADD for p in patches)
    assert by_attribute["standardFieldVisibility.Notes"].new_value is True


def test_changed_standard_field_visibility_field_emits_update(offline_session) -> None:
    """Test that only the changed sub-field of standard_field_visibility is patched."""
    existing = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=True, due_date=False
        )
    )
    updated = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=False, due_date=False
        )
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert len(patches) == 1
    assert patches[0].attribute == "standardFieldVisibility.Tags"
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].old_value is True
    assert patches[0].new_value is False


def test_unchanged_standard_field_visibility_emits_no_op(offline_session) -> None:
    """Test that identical standard_field_visibility values emit no patches."""
    existing = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=True, due_date=False
        )
    )
    updated = _entity_type(
        standard_field_visibility=EntityTypeStandardFieldVisibility(
            notes=True, tags=True, due_date=False
        )
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert patches == []


def test_changed_standard_field_required_field_emits_update(offline_session) -> None:
    """Test that a changed standard_field_required sub-field emits an update op."""
    existing = _entity_type(
        standard_field_required=EntityTypeStandardFieldRequired(
            notes=False, tags=False, due_date=False
        )
    )
    updated = _entity_type(
        standard_field_required=EntityTypeStandardFieldRequired(
            notes=False, tags=False, due_date=True
        )
    )

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert len(patches) == 1
    assert patches[0].attribute == "standardFieldRequired.DueDate"
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].old_value is False
    assert patches[0].new_value is True


def test_new_search_query_string_field_emits_add(offline_session) -> None:
    """Test that a first-time search_query_string sub-field emits an add op."""
    existing = _entity_type()
    updated = _entity_type(search_query_string=EntityTypeSearchQueryStrings(DAT="field={f}"))

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    by_attribute = {p.attribute: p for p in patches}
    assert by_attribute["searchQueryString.DAT"].operation == PatchOperation.ADD
    assert by_attribute["searchQueryString.DAT"].new_value == "field={f}"
    # PRG stayed None on both sides: no patch for it.
    assert "searchQueryString.PRG" not in by_attribute


def test_changed_search_query_string_field_emits_update(offline_session) -> None:
    """Test that a changed search_query_string sub-field emits an update op with old value."""
    existing = _entity_type(search_query_string=EntityTypeSearchQueryStrings(DAT="field={f}"))
    updated = _entity_type(search_query_string=EntityTypeSearchQueryStrings(DAT="field2={f}"))

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert len(patches) == 1
    assert patches[0].attribute == "searchQueryString.DAT"
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].old_value == "field={f}"
    assert patches[0].new_value == "field2={f}"


def test_unset_search_query_string_emits_no_patches(offline_session) -> None:
    """Test that an unset search_query_string emits no patches for its sub-fields."""
    existing = _entity_type(search_query_string=EntityTypeSearchQueryStrings(DAT="field={f}"))
    updated = _entity_type()  # search_query_string never set

    patches = EntityTypeCollection(session=offline_session)._generate_special_attribute_patches(
        existing=existing, updated=updated
    )

    assert patches == []
