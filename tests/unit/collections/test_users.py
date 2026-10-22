"""Unit tests for the user update patch builder.

Allowed under the patch-builder exception in OPINIONS.md: these guard that role,
location, class and witnesser changes are sent in the shapes the users API takes,
that values carried along unchanged send nothing, and that clearing a role or
location warns instead of building a patch the platform would reject.
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
        witnesser=False,
    )


def _patches(offline_session, *, updated: User, existing: User | None = None) -> list[dict]:
    payload = UserCollection(session=offline_session)._generate_patch_payload(
        existing=existing or _existing(), updated=updated
    )
    return payload.model_dump(mode="json", by_alias=True)["data"]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (
            "roles",
            [Role(id="ROL3", name="Other")],
            {"operation": "update", "attribute": "role", "oldValue": "ROL1", "newValue": "ROL3"},
        ),
        (
            "location",
            EntityLink(id="LOC2"),
            {
                "operation": "update",
                "attribute": "locationId",
                "oldValue": "LOC1",
                "newValue": "LOC2",
            },
        ),
        (
            "user_class",
            UserClass.PRIVILEGED,
            {
                "operation": "update",
                "attribute": "userClass",
                "oldValue": "standard",
                "newValue": "privileged",
            },
        ),
        (
            "witnesser",
            True,
            {"operation": "update", "attribute": "witnesser", "oldValue": False, "newValue": True},
        ),
    ],
)
def test_changed_field_is_patched_alongside_other_changes(offline_session, field, value, expected):
    """Test that each field is sent in the users API's shape, next to the name change."""
    updated = User(id="USR1", name="Ada King", **{field: value})

    assert _patches(offline_session, updated=updated) == [
        {"operation": "update", "attribute": "name", "oldValue": "Ada", "newValue": "Ada King"},
        expected,
    ]


def test_fields_matching_current_values_send_nothing(offline_session):
    """Test that unchanged linked values compare by ID, so only the name update is emitted."""
    updated = User(
        id="USR1",
        name="Ada King",
        location=EntityLink(id="LOC1"),
        roles=[Role(id="ROL1", name="Administrators")],
        user_class=UserClass.STANDARD,
        witnesser=False,
    )

    assert [p["attribute"] for p in _patches(offline_session, updated=updated)] == ["name"]


def test_unset_fields_send_nothing(offline_session):
    """Test that leaving the fields unset emits only the requested change."""
    updated = User(id="USR1", name="Ada King")

    assert [p["attribute"] for p in _patches(offline_session, updated=updated)] == ["name"]


def test_adding_role_and_location_to_user_without_them(offline_session):
    """Test that a first role is added as a list and a first location by ID."""
    existing = User(id="USR1", name="Ada")
    updated = User(
        id="USR1",
        name="Ada",
        roles=[Role(id="ROL1", name="Admin")],
        location=EntityLink(id="LOC1"),
    )

    assert _patches(offline_session, updated=updated, existing=existing) == [
        {"operation": "add", "attribute": "role", "newValue": ["ROL1"]},
        {"operation": "add", "attribute": "locationId", "newValue": "LOC1"},
    ]


def test_clearing_role_and_location_warns_and_sends_nothing(offline_session):
    """Test that clearing the role or location warns and no patch is emitted."""
    updated = User(id="USR1", name="Ada", roles=[], location=None)

    with pytest.warns(UserWarning, match="cannot remove") as record:
        patches = _patches(offline_session, updated=updated)

    assert patches == []
    assert sorted(str(w.message) for w in record) == [
        "update() cannot remove location, so the change was ignored.",
        "update() cannot remove roles, so the change was ignored.",
    ]


def test_clearing_absent_role_and_location_sends_nothing(offline_session):
    """Test that clearing a role or location the user does not have emits nothing."""
    existing = User(id="USR1", name="Ada")
    updated = User(id="USR1", name="Ada", roles=[], location=None)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        patches = _patches(offline_session, updated=updated, existing=existing)

    assert patches == []
