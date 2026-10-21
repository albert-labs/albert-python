"""Unit tests for the user update patch builder.

Allowed under the patch-builder exception in OPINIONS.md: these guard that changes to
fields the user update cannot apply warn instead of being dropped silently.
"""

import warnings

import pytest

from albert.collections.users import UserCollection
from albert.core.shared.models.base import EntityLink
from albert.resources.roles import Role
from albert.resources.users import User, UserClass


def _existing() -> User:
    return User(
        id="USR1",
        name="Ada",
        email="ada@example.com",
        location=EntityLink(id="LOC1", name="Lab A"),
        roles=[Role(id="ROL1", name="Admin")],
        user_class=UserClass.STANDARD,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("location", EntityLink(id="LOC2")),
        ("roles", [Role(id="ROL3", name="Other")]),
        ("user_class", UserClass.PRIVILEGED),
        ("witnesser", True),
    ],
)
def test_changed_non_updatable_field_warns_and_applies_other_changes(
    offline_session, field, value
):
    """Test that a field the user update cannot apply is named in a warning and the rest applies."""
    updated = User(id="USR1", name="Ada King", **{field: value})

    with pytest.warns(UserWarning, match=field):
        payload = UserCollection(session=offline_session)._generate_patch_payload(
            existing=_existing(), updated=updated
        )

    assert [(p.operation, p.attribute, p.new_value) for p in payload.data] == [
        ("update", "name", "Ada King")
    ]


def test_non_updatable_fields_matching_current_values_do_not_warn(offline_session):
    """Test that unchanged linked values compare by ID, so only the name update is emitted."""
    updated = User(
        id="USR1",
        name="Ada King",
        location=EntityLink(id="LOC1"),
        roles=[Role(id="ROL1", name="Administrators")],
        user_class=UserClass.STANDARD,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        payload = UserCollection(session=offline_session)._generate_patch_payload(
            existing=_existing(), updated=updated
        )

    assert [(p.operation, p.attribute, p.new_value) for p in payload.data] == [
        ("update", "name", "Ada King")
    ]


def test_unset_non_updatable_fields_do_not_warn(offline_session):
    """Test that leaving non-updatable fields unset emits only the requested change."""
    updated = User(id="USR1", name="Ada King")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        payload = UserCollection(session=offline_session)._generate_patch_payload(
            existing=_existing(), updated=updated
        )

    assert [(p.operation, p.attribute) for p in payload.data] == [("update", "name")]


def test_setting_location_on_user_without_one_warns(offline_session):
    """Test that adding a location to a user with none warns."""
    existing = User(id="USR1", name="Ada")
    updated = User(id="USR1", name="Ada", location=EntityLink(id="LOC1"))

    with pytest.warns(UserWarning, match="location"):
        UserCollection(session=offline_session)._generate_patch_payload(
            existing=existing, updated=updated
        )
