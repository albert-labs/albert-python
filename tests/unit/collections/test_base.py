"""Unit tests for metadata PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard non-obvious
diff behavior in ``BaseCollection._generate_metadata_diff`` with no I/O to fake.
"""

from albert.collections.base import BaseCollection
from albert.collections.companies import CompanyCollection
from albert.core.shared.models.base import BaseResource, EntityLink
from albert.core.shared.models.patch import PatchOperation
from albert.core.shared.types import MetadataItem
from albert.resources.companies import Company


class _Widget(BaseResource):
    """A minimal resource with scalar, list, and metadata fields.

    Used to exercise the generic ``_generate_patch_payload`` matrix independent
    of any single collection's special-cased attributes.
    """

    id: str | None = None
    name: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, MetadataItem] | None = None


class _WidgetCollection(BaseCollection):
    _updatable_attributes = {"name", "tags", "metadata"}


class _Counter(BaseResource):
    """A minimal resource with a numeric field, for exercising stringify_values."""

    id: str | None = None
    count: int | None = None


class _CounterCollection(BaseCollection):
    _updatable_attributes = {"count"}


def test_metadata_add_single_item_list_stays_a_list() -> None:
    """Test a one-item list metadata ADD keeps list cardinality.

    The API stores an ADD newValue verbatim, so collapsing a single-item list to
    a scalar corrupts the field's type on the server.
    """
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"listField": [EntityLink(id="LST1")]},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].attribute == "Metadata.listField"
    assert data[0].new_value == ["LST1"]


def test_metadata_add_multi_item_list_unchanged() -> None:
    """Test a multi-item list metadata ADD still sends all ids as a list."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].new_value == ["LST1", "LST2"]


def test_metadata_add_scalar_unchanged() -> None:
    """Test a scalar metadata ADD still sends the bare value."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"textField": "value"},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].new_value == "value"


def test_metadata_delete_scalar_when_key_removed() -> None:
    """Test that a scalar metadata key dropped from updated_metadata emits a delete op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"textField": "value"},
        updated_metadata={},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.DELETE
    assert data[0].attribute == "Metadata.textField"
    assert data[0].old_value == "value"


def test_metadata_delete_single_item_list_collapses_to_scalar() -> None:
    """Test that deleting a one-item list metadata value sends a bare scalar oldValue.

    Asymmetric with ADD (which always keeps list cardinality): a DELETE oldValue
    for a single-item list collapses to the bare id.
    """
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": [EntityLink(id="LST1")]},
        updated_metadata={},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.DELETE
    assert data[0].old_value == "LST1"


def test_metadata_delete_multi_item_list_stays_a_list() -> None:
    """Test that deleting a multi-item list metadata value keeps the list of ids."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
        updated_metadata={},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.DELETE
    assert data[0].old_value == ["LST1", "LST2"]


def test_metadata_delete_single_entity_value_uses_id() -> None:
    """Test that a non-list, non-scalar metadata value (a single link) deletes by its id."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"linkField": EntityLink(id="LST1")},
        updated_metadata={},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.DELETE
    assert data[0].old_value == "LST1"


def test_metadata_update_scalar_changed() -> None:
    """Test that a changed scalar metadata value emits an update op with old and new values."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"textField": "old"},
        updated_metadata={"textField": "new"},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.UPDATE
    assert data[0].old_value == "old"
    assert data[0].new_value == "new"


def test_metadata_list_membership_unchanged_emits_no_op() -> None:
    """Test that a reordered but membership-unchanged list metadata value emits no op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
        updated_metadata={"listField": [EntityLink(id="LST2"), EntityLink(id="LST1")]},
    )

    assert data == []


def test_metadata_list_cleared_to_empty_emits_delete() -> None:
    """Test that clearing a list metadata value to [] emits a delete op with all old ids."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
        updated_metadata={"listField": []},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.DELETE
    assert data[0].old_value == ["LST1", "LST2"]


def test_metadata_list_membership_changed_emits_whole_list_update() -> None:
    """Test that a changed list metadata value emits a single whole-list update op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": [EntityLink(id="LST1")]},
        updated_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.UPDATE
    assert data[0].old_value == ["LST1"]
    assert data[0].new_value == ["LST1", "LST2"]


def test_metadata_single_entity_value_changed_emits_update_by_id() -> None:
    """Test that a changed single-link metadata value emits an update op keyed by id."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"linkField": EntityLink(id="LST1")},
        updated_metadata={"linkField": EntityLink(id="LST2")},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.UPDATE
    assert data[0].old_value == "LST1"
    assert data[0].new_value == "LST2"


class _DeletableNameCollection(BaseCollection):
    _updatable_attributes = {"name"}


def _company_with_name_cleared() -> Company:
    # ``name`` is required on the model, so bypass validation to build the
    # "explicitly set to None" state an update payload would carry.
    return Company.model_construct(id="COM123", name=None)


def test_delete_op_emitted_by_default() -> None:
    """Test that clearing an updatable attribute emits a delete op by default."""
    existing = Company(id="COM123", name="Acme Chemicals")
    updated = _company_with_name_cleared()

    payload = _DeletableNameCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].attribute == "name"


def test_non_deletable_attributes_skip_delete_ops() -> None:
    """Test that no delete op is emitted for a non-deletable attribute set to None."""
    existing = Company(id="COM123", name="Acme Chemicals")
    updated = _company_with_name_cleared()

    payload = CompanyCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_unset_attribute_emits_no_op() -> None:
    """Test that a field the caller never set produces no patch operation."""
    existing = _Widget(id="W1", name="old", tags=["a"])
    updated = _Widget(id="W1", name="old")  # tags never set

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_none_emits_delete_op() -> None:
    """Test that explicitly clearing a field to None emits a delete op with the old value."""
    existing = _Widget(id="W1", tags=["a", "b"])
    updated = _Widget(id="W1", tags=None)

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].attribute == "tags"
    assert payload.data[0].old_value == ["a", "b"]


def test_explicit_empty_list_emits_update_not_no_op() -> None:
    """Test that clearing a list to [] is an update, never a silent no-op."""
    existing = _Widget(id="W1", tags=["a", "b"])
    updated = _Widget(id="W1", tags=[])

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].attribute == "tags"
    assert payload.data[0].old_value == ["a", "b"]
    assert payload.data[0].new_value == []


def test_changed_scalar_emits_update_with_old_value() -> None:
    """Test that a changed scalar field emits an update op carrying the old value."""
    existing = _Widget(id="W1", name="old")
    updated = _Widget(id="W1", name="new")

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].attribute == "name"
    assert payload.data[0].old_value == "old"
    assert payload.data[0].new_value == "new"


def test_unchanged_scalar_emits_no_op() -> None:
    """Test that setting a field to its existing value produces no patch operation."""
    existing = _Widget(id="W1", name="same")
    updated = _Widget(id="W1", name="same")

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_metadata_delegates_to_metadata_diff_by_default() -> None:
    """Test that the metadata field is diffed by _generate_metadata_diff by default."""
    existing = _Widget(id="W1", metadata={"textField": "a"})
    updated = _Widget(id="W1", metadata={"textField": "b"})

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "Metadata.textField"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "a"
    assert payload.data[0].new_value == "b"


def test_metadata_diff_disabled_treats_metadata_as_a_whole_value() -> None:
    """Test that generate_metadata_diff=False bypasses per-key metadata diffing."""
    existing = _Widget(id="W1", metadata={"textField": "a"})
    updated = _Widget(id="W1", metadata={"textField": "b"})

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated, generate_metadata_diff=False
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "metadata"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == {"textField": "a"}
    assert payload.data[0].new_value == {"textField": "b"}


def test_generate_patch_payload_new_scalar_value_emits_add() -> None:
    """Test that a scalar field set for the first time (old None) emits an add op."""
    existing = _Widget(id="W1")  # name unset -> None
    updated = _Widget(id="W1", name="new")

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "name"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "new"


def test_generate_patch_payload_none_to_empty_list_is_a_no_op() -> None:
    """Test that None (existing) to explicit [] (updated) normalizes to no operation."""
    existing = _Widget(id="W1")  # tags unset -> None
    updated = _Widget(id="W1", tags=[])

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_generate_patch_payload_empty_list_to_none_is_a_no_op() -> None:
    """Test that explicit [] (existing) to explicit None (updated) normalizes to no operation."""
    existing = _Widget(id="W1", tags=[])
    updated = _Widget(id="W1", tags=None)

    payload = _WidgetCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_generate_patch_payload_stringify_values_on_add() -> None:
    """Test that stringify_values=True converts a new numeric value to a string on add."""
    existing = _Counter(id="C1")  # count unset -> None
    updated = _Counter(id="C1", count=5)

    payload = _CounterCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated, stringify_values=True
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "5"


def test_metadata_none_inputs_are_treated_as_empty_dicts() -> None:
    """Test that passing None for either metadata dict is treated as an empty dict."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata=None,
        updated_metadata=None,
    )

    assert data == []


def test_metadata_delete_empty_list_value_emits_no_op() -> None:
    """Test that a removed key whose existing value is an empty list emits no op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"listField": []},
        updated_metadata={},
    )

    assert data == []


def test_metadata_unchanged_scalar_key_present_in_both_emits_no_op() -> None:
    """Test that a scalar key present in both metadata dicts with the same value emits no op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={"textField": "same"},
        updated_metadata={"textField": "same"},
    )

    assert data == []


def test_metadata_add_empty_list_value_emits_no_op() -> None:
    """Test that a new key whose value is an empty list emits no op."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"listField": []},
    )

    assert data == []


def test_metadata_add_single_entity_value_uses_bare_id() -> None:
    """Test that a new key holding a single link (not a list) adds by its bare id."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"linkField": EntityLink(id="LST1")},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].new_value == "LST1"
