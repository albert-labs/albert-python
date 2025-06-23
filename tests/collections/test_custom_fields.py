from albert.albert import Albert
from albert.resources.custom_fields import CustomField


def test_get_by_id(client: Albert, static_custom_fields: list[CustomField]):
    cf = client.custom_fields.get_by_id(id=static_custom_fields[0].id)
    assert cf.id == static_custom_fields[0].id


def test_get_by_name(client: Albert, static_custom_fields: list[CustomField]):
    cf = client.custom_fields.get_by_name(
        name=static_custom_fields[0].name, service=static_custom_fields[0].service
    )
    assert cf.id == static_custom_fields[0].id
    assert cf.name == static_custom_fields[0].name


def test_update(client: Albert, static_custom_fields: list[CustomField]):
    # Custom fields are preloaded and fixed, so we can't modify them without affecting other test runs
    # Just set hidden = True to test the update call, even though the value may not be changing
    cf = static_custom_fields[0].model_copy()
    original_lookup_column = cf.lookup_column
    # original_required = cf.required
    # original_multiselect = cf.multiselect
    # original_pattern = cf.pattern
    # original_default = cf.default
    cf.lookup_column = not cf.lookup_column
    # cf.required = not cf.required
    # cf.multiselect = not cf.multiselect
    # cf.pattern = "test"
    # cf.default = "test"
    cf = client.custom_fields.update(custom_field=cf)
    assert original_lookup_column != cf.lookup_column
    # assert original_required != cf.required
    # assert original_multiselect != cf.multiselect
    # assert original_pattern != cf.pattern
    # assert original_default != cf.default
