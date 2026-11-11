from contextlib import suppress
from uuid import uuid4

import pytest

from albert import Albert
from albert.exceptions import NotFoundError
from albert.resources.custom_fields import CustomField, FieldType
from albert.resources.entity_types import (
    EntityType,
    EntityTypeRule,
    EntityTypeRuleAction,
    EntityTypeRuleTrigger,
    EntityTypeRuleTriggerCase,
    EntityTypeSearchQueryStrings,
)

pytestmark = pytest.mark.xdist_group("entitytypes")


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


def test_update_adds_unset_search_query_string(
    client: Albert, seeded_entity_types: list[EntityType]
):
    """Test setting a search query string that was not previously configured."""
    entity_type = client.entity_types.get_by_id(id=seeded_entity_types[0].id)
    assert entity_type.search_query_string is None

    entity_type.search_query_string = EntityTypeSearchQueryStrings(DAT="status=active")
    updated = client.entity_types.update(entity_type=entity_type)

    assert updated.search_query_string is not None
    assert updated.search_query_string.DAT == "status=active"


def test_entity_type_delete_rule(
    client: Albert,
    seeded_entity_types: list[EntityType],
    static_entity_custom_fields: list[CustomField],
):
    """A rule added via set_rules is removed by delete_rule without touching other rules."""
    entity_type = seeded_entity_types[0]
    # The multiselect list field cannot be a trigger (the API rejects rules on
    # multiselect fields), so the string field triggers and the list field is the target.
    trigger_field = next(
        cf for cf in static_entity_custom_fields if cf.field_type == FieldType.STRING
    )
    target_field = next(
        cf for cf in static_entity_custom_fields if cf.field_type == FieldType.LIST
    )
    rule = EntityTypeRule(
        custom_field_id=trigger_field.id,
        trigger=EntityTypeRuleTrigger(
            cases=[
                EntityTypeRuleTriggerCase(
                    value=f"SDK-Test Trigger {uuid4().hex[:8]}",
                    actions=[
                        EntityTypeRuleAction(
                            target_field=target_field.name,
                            target_field_id=target_field.id,
                            hidden=True,
                        )
                    ],
                )
            ]
        ),
    )
    [created] = client.entity_types.set_rules(id=entity_type.id, rules=[rule])
    assert created.id is not None

    try:
        client.entity_types.delete_rule(id=entity_type.id, rule_id=created.id)

        remaining = client.entity_types.get_rules(id=entity_type.id)
        assert created.id not in {r.id for r in remaining}
    finally:
        with suppress(NotFoundError):
            client.entity_types.delete_rule(id=entity_type.id, rule_id=created.id)


def test_entity_type_delete_rule_not_found(client: Albert, seeded_entity_types: list[EntityType]):
    """Deleting a rule that does not exist raises NotFoundError."""
    with pytest.raises(NotFoundError):
        client.entity_types.delete_rule(id=seeded_entity_types[0].id, rule_id="RUL999999999")
