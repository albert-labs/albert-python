from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Any

from albert import Albert
from albert.resources.attachments import Attachment, AttachmentCategory, AttachmentMetadata
from albert.resources.files import FileInfo
from albert.resources.hazards import HazardStatement, HazardSymbol
from albert.resources.inventory import InventoryItem
from albert.resources.notes import Note
from albert.resources.projects import Project


def _metadata_as_dict(metadata: AttachmentMetadata | dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, AttachmentMetadata):
        return metadata.model_dump(by_alias=True, mode="json", exclude_none=True)
    return dict(metadata)


def test_attach_file_to_note(
    client: Albert,
    static_image_file: FileInfo,
    attachment_note: Note,
):
    """Attach a file to a note and verify it appears on the note."""
    attachment = client.attachments.attach_file_to_note(
        note_id=attachment_note.id,
        file_name=static_image_file.name,
        file_key=static_image_file.name,
    )
    deleted = False
    try:
        updated_note = client.notes.get_by_id(id=attachment_note.id)
        attachment_ids = [x.id for x in updated_note.attachments]
        assert attachment.id in attachment_ids

        client.attachments.delete(id=attachment.id)
        deleted = True
        second_updated_note = client.notes.get_by_id(id=attachment_note.id)
        if second_updated_note.attachments is not None:
            second_attachment_ids = [x.id for x in second_updated_note.attachments]
            assert attachment.id not in second_attachment_ids
        else:
            assert True  # It being None is also fine/ prooves the delete
    finally:
        if not deleted:
            with suppress(Exception):
                client.attachments.delete(id=attachment.id)


def test_upload_and_attach_file_as_note(
    client: Albert,
    static_image_file: FileInfo,
    seeded_inventory: list[InventoryItem],
):
    """Upload a file and attach it to a new note."""
    task = seeded_inventory[0]
    with open("tests/data/dontpanic.jpg", "rb") as file:
        file_data = file.read()
        note = client.attachments.upload_and_attach_file_as_note(
            parent_id=task.id,
            file_name=static_image_file.name,
            file_data=file_data,
            note_text="This is a test note",
        )
    assert isinstance(note, Note)


def test_attachment_create(
    client: Albert,
    static_image_file: FileInfo,
    attachment_note: Note,
):
    """Create an attachment and validate the response."""
    attachment = Attachment(
        parent_id=attachment_note.id,
        name=static_image_file.name,
        key=static_image_file.name,
        namespace="result",
        category=AttachmentCategory.OTHER,
    )
    created = client.attachments.create(attachment=attachment)
    try:
        assert isinstance(created, Attachment)
    finally:
        client.attachments.delete(id=created.id)


def test_upload_and_attach_sds_to_inventory_item(
    client: Albert,
    seeded_inventory: list[InventoryItem],
):
    """Upload an SDS and attach it to an inventory item."""
    attachment = client.attachments.upload_and_attach_sds_to_inventory_item(
        inventory_id=seeded_inventory[0].id,
        file_sds=Path("tests/data/SDS_HCL.pdf"),
        revision_date=date(2024, 12, 1),
        storage_class="10-13",
        un_number="N/A",
    )
    try:
        assert isinstance(attachment, Attachment)
        assert attachment.revision_date == date(2024, 12, 1)
    finally:
        client.attachments.delete(id=attachment.id)


def test_attachment_update(
    client: Albert,
    seeded_inventory: list[InventoryItem],
):
    """Update an SDS attachment and verify multiple writable fields persist."""
    created_attachment = client.attachments.upload_and_attach_sds_to_inventory_item(
        inventory_id=seeded_inventory[0].id,
        file_sds=Path("tests/data/SDS_HCL.pdf"),
        revision_date=date(2024, 12, 1),
        storage_class="10-13",
        un_number="N/A",
    )
    try:
        current_attachment = client.attachments.get_by_id(id=created_attachment.id)
        current_attachment.revision_date = date(2024, 12, 2)
        if not isinstance(current_attachment.metadata, AttachmentMetadata):
            current_attachment.metadata = AttachmentMetadata.model_validate(
                current_attachment.metadata or {}
            )
        current_attachment.name = "updated-sds.pdf"
        current_attachment.metadata.jurisdiction_code = "BR"
        current_attachment.metadata.language_code = "ES"
        current_attachment.metadata.storage_class = "10"
        current_attachment.metadata.wgk = "2"
        current_attachment.metadata.description = "Updated SDS description"
        current_attachment.metadata.hazard_statement = [
            HazardStatement(id="H206 - Desensitized explosives - Category 1", name=None),
            HazardStatement(id="H207 - Desensitized explosives - Category 2", name=None),
        ]
        current_attachment.metadata.symbols = [
            HazardSymbol(id="GHS07", name="Exclamation Mark", status="active")
        ]

        updated = client.attachments.update(attachment=current_attachment)

        assert updated.name == "updated-sds.pdf"
        assert updated.revision_date == date(2024, 12, 2)
        updated_metadata = _metadata_as_dict(updated.metadata)
        assert updated_metadata.get("storageClass") == "10"
        assert updated_metadata.get("jurisdictionCode") == "BR"
        assert updated_metadata.get("languageCode") == "ES"
        assert updated_metadata.get("wgk") == "2"
        assert updated_metadata.get("description") == "Updated SDS description"
        assert {
            "H206 - Desensitized explosives - Category 1",
            "H207 - Desensitized explosives - Category 2",
        }.issubset({x["id"] for x in updated_metadata.get("hazardStatement", [])})
        assert {"GHS07"}.issubset({x["id"] for x in updated_metadata.get("Symbols", [])})
    finally:
        client.attachments.delete(id=created_attachment.id)


def test_upload_and_attach_document_to_project(
    client: Albert,
    seeded_projects: list[Project],
):
    """Upload a document and attach it to a project."""
    attachment = client.attachments.upload_and_attach_document_to_project(
        project_id=seeded_projects[0].id,
        file_path=Path("tests/data/dontpanic.jpg"),
    )
    try:
        assert isinstance(attachment, Attachment)
    finally:
        client.attachments.delete(id=attachment.id)
