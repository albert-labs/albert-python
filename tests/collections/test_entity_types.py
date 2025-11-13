from uuid import uuid4

from albert import Albert
from albert.resources.entity_types import EntityType


def test_entity_type_get_by_id(client: Albert, seeded_entity_types: list[EntityType]):
    seeded = seeded_entity_types[0]
    fetched = client.entity_types.get_by_id(id=seeded.id)
    assert isinstance(fetched, EntityType)
    assert fetched.id == seeded.id
    assert fetched.label == seeded.label


def test_entity_type_update(
    client: Albert, seeded_entity_types: list[EntityType], seed_prefix: str
):
    entity_type = client.entity_types.get_by_id(id=seeded_entity_types[0].id)
    entity_type.label = f"{seed_prefix} Updated Entity Type {uuid4().hex[:4]}"
    entity_type.template_based = not bool(entity_type.template_based)
    entity_type.locked_template = entity_type.template_based

    if entity_type.custom_fields:
        entity_type.custom_fields[0].hidden = not entity_type.custom_fields[0].hidden

    if entity_type.standard_field_visibility:
        entity_type.standard_field_visibility.tags = not entity_type.standard_field_visibility.tags

    if entity_type.standard_field_required:
        entity_type.standard_field_required.notes = not entity_type.standard_field_required.notes

    updated = client.entity_types.update(entity_type=entity_type)

    assert isinstance(updated, EntityType)
    assert updated.id == entity_type.id
    assert updated.label == entity_type.label
    assert updated.template_based == entity_type.template_based
    assert updated.locked_template == entity_type.locked_template

    if entity_type.custom_fields:
        assert updated.custom_fields is not None
        assert updated.custom_fields[0].hidden == entity_type.custom_fields[0].hidden

    if entity_type.standard_field_visibility:
        assert updated.standard_field_visibility is not None
        assert updated.standard_field_visibility.tags == entity_type.standard_field_visibility.tags

    if entity_type.standard_field_required:
        assert updated.standard_field_required is not None
        assert updated.standard_field_required.notes == entity_type.standard_field_required.notes
