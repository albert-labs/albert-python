from uuid import uuid4

import pytest

from albert.client import Albert
from albert.resources.custom_fields import (
    CustomField,
    FieldCategory,
    FieldType,
    ListDefault,
    ListDefaultValue,
    NumberDefault,
    ServiceType,
    StringDefault,
)
from albert.resources.lists import ListItem


def get_or_create_custom_field(
    client: Albert, name: str, field_type: FieldType, service: ServiceType, **kwargs
) -> CustomField:
    """
    Retrieves a custom field by name and service, creating it if it doesn't exist.
    Parameters
    ----------
    client : Albert
        The Albert client.
    name : str
        The name of the custom field.
    field_type : FieldType
        The type of the custom field.
    service : ServiceType
        The service the custom field belongs to.
    **kwargs
        Additional attributes for the custom field if it needs to be created.
    Returns
    -------
    CustomField
        The existing or newly created custom field.
    """
    custom_field = client.custom_fields.get_by_name(name=name, service=service)
    if custom_field:
        return custom_field

    if field_type == FieldType.LIST and "category" not in kwargs:
        kwargs["category"] = FieldCategory.USER_DEFINED

    new_custom_field = CustomField(
        name=name,
        field_type=field_type,
        service=service,
        display_name=kwargs.pop("display_name"),
        **kwargs,
    )
    return client.custom_fields.create(custom_field=new_custom_field)


def get_or_create_list_items(
    client: Albert, custom_field_name: str, category: FieldCategory
) -> list[ListItem]:
    names = [f"{custom_field_name} Option {i}" for i in range(0, 2)]
    existing_items = [
        item
        for item in [
            client.lists.get_matching_item(name=name, list_type=custom_field_name)
            for name in names
        ]
        if item is not None
    ]
    existing_names = [item.name for item in existing_items]
    items_to_create = [name for name in names if name not in existing_names]

    new_items = []
    for name in items_to_create:
        new_item = ListItem(name=name, list_type=custom_field_name, category=category)
        created_item = client.lists.create(list_item=new_item)
        new_items.append(created_item)

    return existing_items + new_items


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
    results = list(client.custom_fields.get_all(max_items=10))
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


@pytest.mark.parametrize(
    "field_type, service, initial_attributes, updated_attributes",
    [
        (
            FieldType.STRING,
            ServiceType.PROJECTS,
            {
                "display_name": "Initial String Field",
                "searchable": False,
                "hidden": False,
                "required": False,
                "editable": True,
                "pattern": None,
                "default": None,
            },
            {
                "display_name": "Updated String Field",
                "searchable": True,
                "hidden": False,
                "required": True,
                "editable": False,
                "pattern": r"^[a-zA-Z0-9_]+$",
                "default": StringDefault(value="default string"),
            },
        ),
        (
            FieldType.NUMBER,
            ServiceType.PROJECTS,
            {
                "display_name": "Initial Number Field",
                "hidden": False,
                "required": False,
                "editable": True,
                "min": 0,
                "max": 10,
                "default": None,
            },
            {
                "display_name": "Updated Number Field",
                "hidden": True,
                "required": False,
                "editable": False,
                "min": 1,
                "max": 20,
                "default": NumberDefault(value=5),
            },
        ),
    ],
)
def test_update_custom_field(
    client: Albert,
    field_type: FieldType,
    service: ServiceType,
    initial_attributes: dict,
    updated_attributes: dict,
):
    """Test updating various attributes of a custom field."""
    field_name = f"test_update_{field_type.value}_{service.value}"
    custom_field = get_or_create_custom_field(
        client,
        name=field_name,
        field_type=field_type,
        service=service,
        **initial_attributes,
    )
    if field_type == FieldType.NUMBER:
        initial_attributes = dict(initial_attributes)
        updated_attributes = dict(updated_attributes)

        current_min = (
            custom_field.min if custom_field.min is not None else initial_attributes["min"]
        )
        current_max = (
            custom_field.max if custom_field.max is not None else initial_attributes["max"]
        )

        initial_attributes["min"] = current_min
        initial_attributes["max"] = current_max
        updated_attributes["max"] = current_max + 10

        # API only accepts min updates when new min is smaller than old min.
        updated_attributes["min"] = current_min - 1 if current_min > 0 else current_min
        updated_attributes["default"] = NumberDefault(value=updated_attributes["min"])

    # Reset to initial state first to ensure a consistent starting point
    for key, value in initial_attributes.items():
        setattr(custom_field, key, value)
    custom_field = client.custom_fields.update(custom_field=custom_field)
    for key, value in initial_attributes.items():
        assert getattr(custom_field, key) == value, f"Failed to reset attribute: {key}"

    # Apply the updated attributes
    for key, value in updated_attributes.items():
        setattr(custom_field, key, value)

    updated_field = client.custom_fields.update(custom_field=custom_field)

    for key, value in updated_attributes.items():
        assert getattr(updated_field, key) == value, f"Failed to update attribute: {key}"


def test_update_custom_field_type_list(client: Albert):
    """Test updating various attributes of a custom field."""
    field_type = FieldType.LIST
    service = ServiceType.PROJECTS
    field_name = f"test_update_{field_type.value}_{service.value}"
    list_items = get_or_create_list_items(
        client, custom_field_name=field_name, category=FieldCategory.BUSINESS_DEFINED
    )

    initial_attributes = {
        "display_name": "Initial List Field",
        "searchable": False,
        "hidden": False,
        "multiselect": False,
        "default": ListDefault(
            value=ListDefaultValue(id=list_items[0].id, name=list_items[0].name)
        ),
    }

    updated_attributes = {
        "display_name": "Updated List Field",
        "searchable": True,
        "hidden": True,
        "multiselect": True,
        "default": ListDefault(
            value=[ListDefaultValue(id=list_items[1].id, name=list_items[1].name)]
        ),
    }

    custom_field = get_or_create_custom_field(
        client,
        name=field_name,
        field_type=field_type,
        service=service,
        category=FieldCategory.BUSINESS_DEFINED,
        **initial_attributes,
    )
    # Ensure reset starts from non-multiselect mode so scalar default is valid.
    if custom_field.multiselect:
        custom_field.multiselect = False
        custom_field = client.custom_fields.update(custom_field=custom_field)

    # Reset to initial state first to ensure a consistent starting point
    for key, value in initial_attributes.items():
        setattr(custom_field, key, value)
    custom_field = client.custom_fields.update(custom_field=custom_field)
    for key, value in initial_attributes.items():
        assert getattr(custom_field, key) == value, f"Failed to reset attribute: {key}"

    # API validates default against the current multiselect mode.
    for key in ("display_name", "searchable", "hidden", "multiselect"):
        setattr(custom_field, key, updated_attributes[key])
    custom_field = client.custom_fields.update(custom_field=custom_field)

    custom_field.default = updated_attributes["default"]
    updated_field = client.custom_fields.update(custom_field=custom_field)

    for key, value in updated_attributes.items():
        assert getattr(updated_field, key) == value, f"Failed to update attribute: {key}"


def test_delete_custom_field(client: Albert):
    """Test deleting a custom field by ID."""
    custom_field = CustomField(
        name=f"test_delete_{uuid4().hex[:12]}",
        field_type=FieldType.STRING,
        service=ServiceType.PROJECTS,
        display_name="Delete Test Field",
    )

    created_field = client.custom_fields.create(custom_field=custom_field)
    client.custom_fields.delete(id=created_field.id)

    assert (
        client.custom_fields.get_by_name(name=created_field.name, service=created_field.service)
        is None
    )
