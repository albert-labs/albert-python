from contextlib import suppress
from datetime import date
from pathlib import Path

from albert import Albert
from albert.resources.attachments import Attachment, AttachmentCategory
from albert.resources.files import FileInfo
from albert.resources.inventory import InventoryItem
from albert.resources.notes import Note
from albert.resources.projects import Project


def test_attach_file_to_note(
    client: Albert,
    static_image_file: FileInfo,
    attachment_note: Note,
):
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


def test_upload_document(
    client: Albert,
    seeded_projects: list[Project],
):
    attachment = client.attachments.upload_and_attach_document_to_project(
        project_id=seeded_projects[0].id,
        file_path=Path("tests/data/dontpanic.jpg"),
    )
    try:
        assert isinstance(attachment, Attachment)
    finally:
        client.attachments.delete(id=attachment.id)
