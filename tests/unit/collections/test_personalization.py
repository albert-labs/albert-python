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
        category=None, sub_category=None, user_id=None
    )

    assert params == {"limit": _PERSONALIZATION_PAGE_LIMIT}


def test_get_all_params_sub_category_requires_category() -> None:
    """Test that sub_category without category is rejected."""
    with pytest.raises(ValueError, match="`category` is required"):
        PersonalizationCollection._get_all_params(category=None, sub_category="Task", user_id=None)


def test_get_all_params_user_id_maps_to_created_by() -> None:
    """Test that user_id maps to its wire parameter name."""
    params = PersonalizationCollection._get_all_params(
        category=None, sub_category=None, user_id="USR1"
    )

    assert params["createdBy"] == "USR1"


def test_get_all_params_category_serializes_to_wire_value() -> None:
    """Test that the category enum is sent as its wire string."""
    params = PersonalizationCollection._get_all_params(
        category=PersonalizationCategory.STARRED_PROJECTS,
        sub_category=None,
        user_id="USR1",
    )

    assert params == {
        "limit": _PERSONALIZATION_PAGE_LIMIT,
        "createdBy": "USR1",
        "category": "Starred Projects",
    }
