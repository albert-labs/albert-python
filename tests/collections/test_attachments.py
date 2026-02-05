from datetime import date
from pathlib import Path

import pytest

from albert import Albert
from albert.resources.attachments import Attachment, AttachmentCategory
from albert.resources.files import FileInfo
from albert.resources.inventory import InventoryItem
from albert.resources.notes import Note


@pytest.mark.slow
def test_load_file_to_inventories(
    client: Albert,
    static_image_file: FileInfo,
    seeded_notes: list[Note],
):
    attachment = client.attachments.attach_file_to_note(
        note_id=seeded_notes[0].id,
        file_name=static_image_file.name,
        file_key=static_image_file.name,
    )
    updated_note = client.notes.get_by_id(id=seeded_notes[0].id)
    attachment_ids = [x.id for x in updated_note.attachments]
    assert attachment.id in attachment_ids

    parent_attachments = client.attachments.get_by_parent_ids(parent_ids=[seeded_notes[0].id])
    parent_attachment_ids = [x.id for x in parent_attachments[seeded_notes[0].id]]
    assert attachment.id in parent_attachment_ids

    client.attachments.delete(id=attachment.id)
    second_updated_note = client.notes.get_by_id(id=seeded_notes[0].id)
    if second_updated_note.attachments is not None:
        second_attachment_ids = [x.id for x in second_updated_note.attachments]
        assert attachment.id not in second_attachment_ids
    else:
        assert True  # It being None is also fine/ prooves the delete


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


@pytest.mark.slow
def test_attachment_create(
    client: Albert,
    static_image_file: FileInfo,
    seeded_notes: list[Note],
):
    attachment = Attachment(
        parent_id=seeded_notes[0].id,
        name=static_image_file.name,
        key=static_image_file.name,
        namespace="result",
        category=AttachmentCategory.OTHER,
    )
    created = client.attachments.create(attachment=attachment)
    assert isinstance(created, Attachment)
    client.attachments.delete(id=created.id)


@pytest.mark.slow
def test_upload_and_attach_sds_to_inventory_item(
    client: Albert,
    seeded_inventory: list[InventoryItem],
):
    un_numbers = client.un_numbers.get_all(max_items=1)
    un_number = list(un_numbers)[0]
    attachment = client.attachments.upload_and_attach_sds_to_inventory_item(
        inventory_id=seeded_inventory[0].id,
        file_sds=Path("tests/data/SDS_HCL.pdf"),
        revision_date=date(2024, 12, 1),
        storage_class="10-13",
        un_number=un_number.un_number,
    )
    assert isinstance(attachment, Attachment)
    assert attachment.revision_date == date(2024, 12, 1)
    client.attachments.delete(id=attachment.id)
