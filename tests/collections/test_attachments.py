import pytest

from albert import Albert
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
