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


def test_note_get_by_parent_id(client: Albert, seeded_notes: list[Note]):
    """Test that all returned notes match the given parent ID."""
    parent_id = seeded_notes[0].parent_id
    results = list(client.notes.get_by_parent_id(parent_id=parent_id))

    assert results, "Expected at least one Note"
    for note in results:
        assert isinstance(note, Note)
        assert note.parent_id == parent_id
