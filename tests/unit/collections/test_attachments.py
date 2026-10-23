"""Unit tests for AttachmentCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_attachment_patch_payload`` (metadata
sub-fields are diffed item-by-item except ``extensions``, which is a
whole-value update) with no I/O to fake.
"""

from datetime import date

from albert.collections.attachments import AttachmentCollection
from albert.core.shared.models.base import EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.resources.attachments import Attachment, AttachmentMetadata
from albert.resources.hazards import HazardStatement, HazardSymbol


def _attachment(**kwargs) -> Attachment:
    defaults = {"id": "ATT1", "parent_id": "INVA1", "name": "sds.pdf", "key": "INVA1/sds.pdf"}
    defaults.update(kwargs)
    return Attachment(**defaults)


def test_unset_top_level_fields_emit_no_ops(offline_session) -> None:
    """Test that top-level fields the caller never set produce no patch operations."""
    existing = _attachment(revision_date=date(2024, 1, 1))
    updated = _attachment()  # revision_date, name, parent_id all unchanged/unset relative

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_none_revision_date_emits_delete(offline_session) -> None:
    """Test that explicitly clearing revision_date emits a delete op."""
    existing = _attachment(revision_date=date(2024, 1, 1))
    updated = _attachment(revision_date=None)

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "revisionDate"
    assert payload.data[0].operation == PatchOperation.DELETE


def test_changed_name_emits_update(offline_session) -> None:
    """Test that a changed top-level field (name) emits an update op with the old value."""
    existing = _attachment(name="old.pdf")
    updated = _attachment(name="new.pdf")

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "name"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "old.pdf"
    assert payload.data[0].new_value == "new.pdf"


def test_unset_metadata_emits_no_metadata_ops(offline_session) -> None:
    """Test that unset metadata short-circuits: no metadata sub-field diffing occurs."""
    existing = _attachment(metadata=AttachmentMetadata(wgk="1"))
    updated = _attachment()  # metadata never set

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_new_scalar_metadata_field_emits_add(offline_session) -> None:
    """Test that a new scalar metadata value emits an add op."""
    existing = _attachment(metadata=AttachmentMetadata())
    updated = _attachment(metadata=AttachmentMetadata(wgk="2"))

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "wgk"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "2"


def test_cleared_scalar_metadata_field_emits_delete(offline_session) -> None:
    """Test that clearing a scalar metadata value emits a delete op with the old value."""
    existing = _attachment(metadata=AttachmentMetadata(wgk="1"))
    updated = _attachment(metadata=AttachmentMetadata(wgk=None))

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "wgk"
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].old_value == "1"


def test_changed_scalar_metadata_field_emits_update(offline_session) -> None:
    """Test that a changed scalar metadata value emits an update op."""
    existing = _attachment(metadata=AttachmentMetadata(wgk="1"))
    updated = _attachment(metadata=AttachmentMetadata(wgk="2"))

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "wgk"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "1"
    assert payload.data[0].new_value == "2"


def test_unchanged_scalar_metadata_field_emits_no_op(offline_session) -> None:
    """Test that an unchanged scalar metadata value emits no patch operation."""
    existing = _attachment(metadata=AttachmentMetadata(wgk="1"))
    updated = _attachment(metadata=AttachmentMetadata(wgk="1"))

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_added_symbol_emits_add_wrapped_as_id_object(offline_session) -> None:
    """Test that a newly added Symbols entry emits an add op wrapped as [{"id": ...}]."""
    existing = _attachment(metadata=AttachmentMetadata(symbols=[]))
    updated = _attachment(
        metadata=AttachmentMetadata(symbols=[HazardSymbol(id="HAZ1", name="Corrosive")])
    )

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "Symbols"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == [{"id": "HAZ1"}]


def test_removed_symbol_emits_delete_wrapped_as_id_object(offline_session) -> None:
    """Test that a removed Symbols entry emits a delete op wrapped as [{"id": ...}]."""
    existing = _attachment(
        metadata=AttachmentMetadata(symbols=[HazardSymbol(id="HAZ1", name="Corrosive")])
    )
    updated = _attachment(metadata=AttachmentMetadata(symbols=[]))

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "Symbols"
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].old_value == [{"id": "HAZ1"}]


def test_unchanged_symbols_emits_no_op(offline_session) -> None:
    """Test that an unchanged Symbols list emits no patch operation."""
    existing = _attachment(
        metadata=AttachmentMetadata(symbols=[HazardSymbol(id="HAZ1", name="Corrosive")])
    )
    updated = _attachment(
        metadata=AttachmentMetadata(symbols=[HazardSymbol(id="HAZ1", name="Corrosive")])
    )

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_added_hazard_statement_emits_add_with_bare_id(offline_session) -> None:
    """Test that a newly added hazardStatement entry emits an add op with a bare id.

    Unlike Symbols, hazardStatement item ops are not wrapped as [{"id": ...}].
    """
    existing = _attachment(metadata=AttachmentMetadata(hazard_statement=[]))
    updated = _attachment(
        metadata=AttachmentMetadata(
            hazard_statement=[HazardStatement(id="HS1", name="Causes skin irritation")]
        )
    )

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "hazardStatement"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "HS1"


def test_extensions_change_emits_whole_value_update(offline_session) -> None:
    """Test that extensions are diffed as a single whole-value update, not per item."""
    existing = _attachment(
        metadata=AttachmentMetadata(extensions=[EntityLinkWithName(id="EXT1", name="Ext 1")])
    )
    updated = _attachment(
        metadata=AttachmentMetadata(
            extensions=[
                EntityLinkWithName(id="EXT1", name="Ext 1"),
                EntityLinkWithName(id="EXT2", name="Ext 2"),
            ]
        )
    )

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "extensions"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == [{"id": "EXT1", "name": "Ext 1"}]
    assert payload.data[0].new_value == [
        {"id": "EXT1", "name": "Ext 1"},
        {"id": "EXT2", "name": "Ext 2"},
    ]


def test_unchanged_extensions_emits_no_op(offline_session) -> None:
    """Test that an unchanged extensions list emits no patch operation."""
    existing = _attachment(
        metadata=AttachmentMetadata(extensions=[EntityLinkWithName(id="EXT1", name="Ext 1")])
    )
    updated = _attachment(
        metadata=AttachmentMetadata(extensions=[EntityLinkWithName(id="EXT1", name="Ext 1")])
    )

    payload = AttachmentCollection(session=offline_session)._generate_attachment_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []
