import pytest

from albert.core.shared.models.base import (
    AuditFields,
    BaseResource,
    BaseSessionResource,
    EntityLink,
    EntityLinkWithName,
    LocalizedNames,
)
from albert.exceptions import AlbertException


def test_audit_fields_alias_round_trip():
    """Test that AuditFields accepts the byName alias and dumps back to it."""
    audit = AuditFields(by="user-1", byName="User One", at="2024-01-01T00:00:00Z")

    assert audit.by_name == "User One"

    dumped = audit.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["by"] == "user-1"
    assert dumped["byName"] == "User One"
    assert dumped["at"].startswith("2024-01-01T00:00:00")
    assert AuditFields.model_validate(dumped).by_name == "User One"


def test_entity_link_to_entity_link_is_identity():
    """Test that calling to_entity_link on an EntityLink returns the same instance."""
    link = EntityLink(id="LNK1", name="ignored")

    assert link.to_entity_link() is link


def test_entity_link_excludes_name_and_category_from_serialization():
    """Test that EntityLink drops name and category when dumped."""
    link = EntityLink(id="LNK1", name="Some Name", category="cat")

    dumped = link.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped == {"id": "LNK1"}


def test_entity_link_with_name_includes_name_in_serialization():
    """Test that EntityLinkWithName keeps name in the wire payload."""
    link = EntityLinkWithName(id="LNK1", name="Some Name", category="cat")

    dumped = link.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped == {"id": "LNK1", "name": "Some Name"}

    round_tripped = EntityLinkWithName.model_validate(dumped)
    assert round_tripped.name == "Some Name"


def test_localized_names_all_fields_optional():
    """Test that LocalizedNames tolerates a missing key for every localized field."""
    names = LocalizedNames.model_validate({"de": "Wasser"})

    assert names.de == "Wasser"
    assert names.ja is None
    assert names.zh is None
    assert names.es is None


class _Widget(BaseResource):
    id: str | None = None
    name: str | None = None


def test_base_resource_to_entity_link_with_id():
    """Test that to_entity_link builds an EntityLink from a non-null id."""
    widget = _Widget(id="WID1", name="thing")

    link = widget.to_entity_link()
    assert isinstance(link, EntityLink)
    assert link.id == "WID1"


def test_base_resource_to_entity_link_without_id_raises():
    """Test that to_entity_link raises when the resource has no id."""
    widget = _Widget.model_construct(id=None, name="thing")

    with pytest.raises(AlbertException, match="non-null 'id' is required"):
        widget.to_entity_link()


def test_base_resource_to_entity_link_with_name_with_id():
    """Test that to_entity_link_with_name carries the name field through."""
    widget = _Widget(id="WID1", name="thing")

    link = widget.to_entity_link_with_name()
    assert isinstance(link, EntityLinkWithName)
    assert link.id == "WID1"
    assert link.name == "thing"


def test_base_resource_to_entity_link_with_name_without_id_raises():
    """Test that to_entity_link_with_name raises when the resource has no id."""
    widget = _Widget.model_construct(id=None, name="thing")

    with pytest.raises(AlbertException, match="non-null 'id' is required"):
        widget.to_entity_link_with_name()


def test_base_session_resource_stores_session():
    """Test that BaseSessionResource captures the session kwarg without exposing it as a field."""
    resource = BaseSessionResource(session="fake-session")

    assert resource.session == "fake-session"
    assert "session" not in resource.model_dump(by_alias=True, exclude_none=True)


def test_base_session_resource_session_defaults_to_none():
    """Test that BaseSessionResource has no session when none is provided."""
    resource = BaseSessionResource()

    assert resource.session is None
