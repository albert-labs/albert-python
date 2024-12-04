from albert import Albert
from albert.resources.notes import Note


def test_get_by_id(client: Albert, seeded_notes: list[Note]):
    note = seeded_notes[0]
    retrieved_note = client.notes.get_by_id(id=note.id)
    assert retrieved_note.note == note.note
    assert retrieved_note.id == note.id


def test_update(client: Albert, seeded_notes: list[Note]):
    note = seeded_notes[1]
    new_str = "TEST- Updated Inventory note"
    note.note = new_str
    updated_note = client.notes.update(note=note)
    assert updated_note.note == new_str
    assert updated_note.id == note.id


def test_list(client: Albert, seeded_notes: list[Note]):
    seeded_parent_id = seeded_notes[0].parent_id
    notes = client.notes.list(parent_id=seeded_parent_id)

    for n in notes:
        assert n.parent_id == seeded_parent_id
        assert isinstance(n, Note)
