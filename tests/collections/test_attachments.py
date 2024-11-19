from albert import Albert

# from albert.resources.attachments import Attachment
from albert.resources.files import FileInfo

# from albert.resources.inventory import InventoryItem
from albert.resources.notes import Note


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
    client.attachments.delete(id=attachment.id)
    second_updated_note = client.notes.get_by_id(id=seeded_notes[0].id)
    second_attachment_ids = [x.id for x in second_updated_note.attachments]
    assert attachment.id not in second_attachment_ids
