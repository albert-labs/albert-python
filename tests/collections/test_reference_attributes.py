from albert.client import Albert
from albert.resources.reference_attributes import ReferenceAttribute


def assert_reference_attribute_items(returned_list: list[ReferenceAttribute]):
    """Assert basic ReferenceAttribute structure and types."""
    assert returned_list, "Expected at least one ReferenceAttribute"
    for item in returned_list[:10]:
        assert isinstance(item, ReferenceAttribute)
        assert isinstance(item.id, str)


def test_reference_attributes_get_all(
    client: Albert, seeded_reference_attributes: list[ReferenceAttribute]
):
    """Test retrieving reference attributes with pagination."""
    results = list(client.reference_attributes.get_all(max_items=5))
    assert_reference_attribute_items(results)


def test_reference_attributes_get_by_id(
    client: Albert, seeded_reference_attributes: list[ReferenceAttribute]
):
    """Test retrieving a reference attribute by id."""
    reference_attribute = seeded_reference_attributes[0]
    fetched = client.reference_attributes.get_by_id(id=reference_attribute.id)
    assert fetched.id == reference_attribute.id
    assert fetched.reference_name == reference_attribute.reference_name


def test_reference_attributes_get_by_ids(
    client: Albert, seeded_reference_attributes: list[ReferenceAttribute]
):
    """Test retrieving reference attributes by bulk ids."""
    ids = [x.id for x in seeded_reference_attributes]
    results = client.reference_attributes.get_by_ids(ids=ids)
    assert len(results) == len(ids)
    assert {x.id for x in results} == set(ids)
