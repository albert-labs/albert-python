import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError, NotFoundError
from albert.resources.cas import Cas
from albert.resources.custom_fields import CustomField, FieldCategory, FieldType, ServiceType
from albert.resources.lists import ListItem, ListItemCategory


@pytest.fixture
def cas_list_metadata_field(client: Albert, seed_prefix: str):
    """Create a list-type CAS custom field and delete it after the test."""
    field_name = f"test_cas_list_{seed_prefix.replace('-', '_')[:20]}".lower()
    custom_field = client.custom_fields.create(
        custom_field=CustomField(
            name=field_name,
            display_name=f"TEST CAS List {seed_prefix[:10]}",
            field_type=FieldType.LIST,
            service=ServiceType.CAS,
            category=FieldCategory.USER_DEFINED,
        )
    )
    try:
        yield field_name, custom_field
    finally:
        with suppress(NotFoundError):
            client.custom_fields.delete(id=custom_field.id)


def _create_cas_list_item(
    client: Albert, *, field_name: str, seed_prefix: str, suffix: str
) -> ListItem:
    return client.lists.create(
        list_item=ListItem(
            name=f"{seed_prefix}-{suffix}",
            category=ListItemCategory.USER_DEFINED,
            list_type=field_name,
        )
    )


def assert_valid_cas_items(items: list[Cas]):
    assert items, "Expected at least one CAS result"
    for c in items[:10]:
        assert isinstance(c, Cas)
        assert isinstance(c.number, str)
        assert not c.name or isinstance(c.name, str)
        assert c.id.startswith("CAS")


def test_cas_get_all_with_pagination(client: Albert):
    """Test that CAS get_all() respects pagination via max_items."""
    simple_list = list(client.cas_numbers.get_all(max_items=10))
    assert_valid_cas_items(simple_list)
    assert len(simple_list) <= 10


def test_cas_get_all_with_filters(client: Albert):
    """Test CAS get_all() with id and cas filters."""
    existing = next(client.cas_numbers.get_all(max_items=1))

    id_list = list(client.cas_numbers.get_all(id=existing.id, max_items=10))
    assert_valid_cas_items(id_list)
    assert id_list[0].id == existing.id

    multi_cas = list(client.cas_numbers.get_all(cas=[existing.number]))
    assert_valid_cas_items(multi_cas)
    assert any(c.number == existing.number for c in multi_cas)


def test_cas_not_found(client: Albert):
    """Test that requesting a CAS by invalid ID raises an error."""
    with pytest.raises(AlbertHTTPError):
        client.cas_numbers.get_by_id(id="foo bar")


def test_cas_exists(client: Albert):
    """Test that exists() returns True for known CAS and False for unknown CAS."""
    existing = next(client.cas_numbers.get_all(max_items=1))
    assert client.cas_numbers.exists(number=existing.number)
    assert not client.cas_numbers.exists(number=str(uuid.uuid4()))


def test_update_cas(client: Albert, seed_prefix: str, seeded_cas: list[Cas]):
    """Test that updating a CAS object reflects changes."""
    if not seeded_cas:
        pytest.skip("No seeded CAS available — stale prod data prevented fixture setup")
    cas_to_update = seeded_cas[0]
    updated_description = f"{seed_prefix} - A new description"
    cas_to_update.description = updated_description

    updated_cas = client.cas_numbers.update(updated_object=cas_to_update)

    assert updated_cas.description == updated_description


def test_update_cas_metadata(client: Albert, seed_prefix: str, seeded_cas: list[Cas]):
    """Test that updating CAS metadata reflects changes."""
    if not seeded_cas:
        pytest.skip("No seeded CAS available — stale prod data prevented fixture setup")
    field_name = f"test_cas_meta_{seed_prefix.replace('-', '_')[:20]}".lower()
    custom_field = client.custom_fields.create(
        custom_field=CustomField(
            name=field_name,
            display_name=f"TEST CAS Meta {seed_prefix[:10]}",
            field_type=FieldType.STRING,
            service=ServiceType.CAS,
        )
    )
    try:
        cas_to_update = seeded_cas[0]
        new_value = f"{seed_prefix} - metadata test"
        cas_to_update.metadata = {**cas_to_update.metadata, field_name: new_value}
        updated_cas = client.cas_numbers.update(updated_object=cas_to_update)
        assert updated_cas.metadata.get(field_name) == new_value
    finally:
        with suppress(NotFoundError):
            client.custom_fields.delete(id=custom_field.id)


def test_create_cas_with_list_metadata(
    client: Albert, seed_prefix: str, cas_list_metadata_field: tuple[str, CustomField]
):
    """Test that creating a CAS with list-type metadata hydrates list item names."""
    field_name, _ = cas_list_metadata_field
    list_item = _create_cas_list_item(
        client, field_name=field_name, seed_prefix=seed_prefix, suffix="list-value"
    )
    cas_number = f"{seed_prefix}-list-meta-50-00-0"
    try:
        created = client.cas_numbers.create(
            cas=Cas(
                number=cas_number,
                metadata={field_name: [EntityLink(id=list_item.id)]},
            )
        )
        links = created.metadata.get(field_name)
        assert links is not None
        assert [link.id for link in links] == [list_item.id]
        assert links[0].name == list_item.name
    finally:
        with suppress(NotFoundError):
            if "created" in locals():
                client.cas_numbers.delete(id=created.id)
        with suppress(NotFoundError):
            client.lists.delete(id=list_item.id)


def test_update_cas_list_metadata(
    client: Albert, seed_prefix: str, cas_list_metadata_field: tuple[str, CustomField]
):
    """Test that updating CAS list-type metadata stores entity links and round-trips."""
    field_name, _ = cas_list_metadata_field
    first_list_item = _create_cas_list_item(
        client, field_name=field_name, seed_prefix=seed_prefix, suffix="list-a"
    )
    second_list_item = _create_cas_list_item(
        client, field_name=field_name, seed_prefix=seed_prefix, suffix="list-b"
    )
    cas_number = f"{seed_prefix}-list-upd-50-00-0"
    try:
        created = client.cas_numbers.create(
            cas=Cas(
                number=cas_number,
                metadata={field_name: [EntityLink(id=first_list_item.id)]},
            )
        )
        existing = client.cas_numbers.get_by_id(id=created.id)
        updated = existing.model_copy(
            update={
                "metadata": {**existing.metadata, field_name: [EntityLink(id=second_list_item.id)]}
            }
        )
        result = client.cas_numbers.update(updated_object=updated)
        assert [link.id for link in result.metadata[field_name]] == [second_list_item.id]
        assert result.metadata[field_name][0].name == second_list_item.name

        refetched = client.cas_numbers.get_by_id(id=created.id)
        assert [link.id for link in refetched.metadata[field_name]] == [second_list_item.id]
        assert refetched.metadata[field_name][0].name == second_list_item.name
    finally:
        with suppress(NotFoundError):
            if "created" in locals():
                client.cas_numbers.delete(id=created.id)
        with suppress(NotFoundError):
            client.lists.delete(id=second_list_item.id)
        with suppress(NotFoundError):
            client.lists.delete(id=first_list_item.id)


def test_get_by_number(client: Albert):
    """Test get_by_number() returns the correct CAS using exact match."""
    existing = next(client.cas_numbers.get_all(max_items=1))
    returned = client.cas_numbers.get_by_number(number=existing.number, exact_match=True)
    assert returned is not None
    assert returned.id == existing.id
    assert returned.number == existing.number


def test_get_or_create_cas(client: Albert):
    """Test get_or_create returns the existing CAS when it already exists."""
    existing = next(client.cas_numbers.get_all(max_items=1))
    fetched = client.cas_numbers.get_or_create(cas=existing.number)
    assert fetched.id == existing.id
