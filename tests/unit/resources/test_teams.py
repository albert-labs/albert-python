import pytest
from pydantic import ValidationError

from albert.resources.teams import Team


def test_merge_acl_ignores_non_dict_input():
    """Test the ACL merge validator leaves non-dict input for downstream validation to reject."""
    with pytest.raises(ValidationError):
        Team.model_validate(["not", "a", "dict"])


def test_merge_acl_skips_when_users_missing():
    """Test that an ACL list with no Users list is left unmerged and members stays unset."""
    team = Team.model_validate({"name": "R&D", "ACL": [{"id": "USR1", "fgc": "TeamOwner"}]})
    assert team.members is None


def test_merge_acl_skips_when_acl_missing():
    """Test that Users without an ACL list are parsed as-is, with no role filled in."""
    team = Team.model_validate({"name": "R&D", "Users": [{"id": "USR1"}]})
    assert team.members[0].role is None


def test_merge_acl_fills_in_missing_role_from_matching_entry():
    """Test that a user's role is filled in from the matching ACL entry by id."""
    team = Team.model_validate(
        {
            "name": "R&D",
            "Users": [{"id": "USR1"}, {"id": "USR2"}],
            "ACL": [
                {"id": "USR1", "fgc": "TeamOwner"},
                {"id": "USR3", "fgc": "TeamViewer"},
            ],
        }
    )
    assert team.members[0].id == "USR1"
    assert team.members[0].role == "TeamOwner"
    # USR2 has no matching ACL entry, so its role stays unset.
    assert team.members[1].role is None


def test_merge_acl_does_not_override_existing_role():
    """Test that a user's explicit role is preserved even when the ACL disagrees."""
    team = Team.model_validate(
        {
            "name": "R&D",
            "Users": [{"id": "USR1", "fgc": "TeamViewer"}],
            "ACL": [{"id": "USR1", "fgc": "TeamOwner"}],
        }
    )
    assert team.members[0].role == "TeamViewer"
