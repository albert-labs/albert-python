from albert.client import Albert
from albert.resources.custom_fields import CustomField


def assert_valid_customfield_items(items: list[CustomField]):
    """Assert basic structure and types of CustomField items."""
    assert items, "Expected at least one CustomField result"
    for item in items[:10]:
        assert isinstance(item, CustomField)
        assert isinstance(item.id, str)
        assert isinstance(item.name, str)
        assert item.id.startswith("CTF")


def test_customfield_get_all_with_pagination(client: Albert):
    """Test CustomField get_all() paginates correctly with small page size."""
    results = list(
        client.custom_fields.get_all(
            max_items=10,
        )
    )
    assert len(results) <= 10
    assert_valid_customfield_items(results)


def test_customfield_get_all_with_filters(client: Albert, static_custom_fields: list[CustomField]):
    """Test CustomField get_all() with filters by name and service."""
    target = static_custom_fields[0]

    filtered = list(
        client.custom_fields.get_all(
            name=target.name,
            service=target.service,
            max_items=10,
        )
    )
    assert any(f.name == target.name for f in filtered)
    assert any(f.service == target.service for f in filtered)
    assert_valid_customfield_items(filtered)


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
