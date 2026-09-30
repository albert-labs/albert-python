"""Unit tests for PersonalizationCollection private helpers.

Covers the pure ``_get_all_params`` query builder, which owns the list
endpoint's filter-combination rules, with no I/O to fake.
"""

import pytest

from albert.collections.personalization import (
    _PERSONALIZATION_PAGE_LIMIT,
    PersonalizationCollection,
)
from albert.resources.personalization import PersonalizationCategory


def test_get_all_params_default_sends_only_page_limit() -> None:
    """Test that no filters produce a bare paginated request."""
    params = PersonalizationCollection._get_all_params(
        category=None, sub_category=None, saved_id=None, user_id=None
    )

    assert params == {"limit": _PERSONALIZATION_PAGE_LIMIT}


def test_get_all_params_saved_id_and_user_id_are_mutually_exclusive() -> None:
    """Test that combining saved_id with user_id is rejected."""
    with pytest.raises(ValueError, match="Only one of"):
        PersonalizationCollection._get_all_params(
            category=None, sub_category=None, saved_id="PRO1", user_id="USR1"
        )


def test_get_all_params_sub_category_requires_category() -> None:
    """Test that sub_category without category is rejected."""
    with pytest.raises(ValueError, match="`category` is required"):
        PersonalizationCollection._get_all_params(
            category=None, sub_category="Task", saved_id=None, user_id=None
        )


@pytest.mark.parametrize(
    ("saved_id", "user_id", "expected_key", "expected_value"),
    [
        ("PRO1", None, "savedId", "PRO1"),
        (None, "USR1", "createdBy", "USR1"),
    ],
)
def test_get_all_params_owner_filters(
    saved_id: str | None, user_id: str | None, expected_key: str, expected_value: str
) -> None:
    """Test that saved_id and user_id map to their wire parameter names."""
    params = PersonalizationCollection._get_all_params(
        category=None, sub_category=None, saved_id=saved_id, user_id=user_id
    )

    assert params[expected_key] == expected_value


def test_get_all_params_category_serializes_to_wire_value() -> None:
    """Test that the category enum is sent as its wire string."""
    params = PersonalizationCollection._get_all_params(
        category=PersonalizationCategory.STARRED_PROJECTS,
        sub_category=None,
        saved_id=None,
        user_id="USR1",
    )

    assert params == {
        "limit": _PERSONALIZATION_PAGE_LIMIT,
        "createdBy": "USR1",
        "category": "Starred Projects",
    }
