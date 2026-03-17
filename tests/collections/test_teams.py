from contextlib import suppress

import pytest
from tenacity import retry, stop_after_delay, wait_fixed

from albert import Albert
from albert.exceptions import AlbertException, NotFoundError
from albert.resources.teams import Team, TeamMember
from albert.resources.users import User


def _assert_member_absent(client: Albert, team_id: str, user_id: str) -> Team:
    """Fetch team and assert user is not a member. Retries for eventual consistency."""

    @retry(stop=stop_after_delay(5), wait=wait_fixed(1), reraise=True)
    def _check():
        team = client.teams.get_by_id(id=team_id)
        assert user_id not in [m.id for m in team.members or []]
        return team

    return _check()


def _assert_member_present(client: Albert, team_id: str, user_id: str) -> Team:
    """Fetch team and assert user is a member. Retries for eventual consistency."""

    @retry(stop=stop_after_delay(5), wait=wait_fixed(1), reraise=True)
    def _check():
        team = client.teams.get_by_id(id=team_id)
        assert user_id in [m.id for m in team.members or []]
        return team

    return _check()


def test_create(client: Albert, seed_prefix: str, static_user: User):
    """Test creating a team with members."""
    team = client.teams.create(
        name=f"{seed_prefix}-create",
        members=[TeamMember(id=static_user.id, role="TeamOwner")],
    )
    try:
        assert team.id is not None
        assert team.id.startswith("TEM")
        assert team.name == f"{seed_prefix}-create"
        assert team.members is not None
        assert static_user.id in [m.id for m in team.members]
    finally:
        with suppress(Exception):
            client.teams.delete(id=team.id)


def test_get_by_id(client: Albert, seeded_team: Team):
    """Test retrieving a team by ID."""
    fetched = client.teams.get_by_id(id=seeded_team.id)
    assert fetched.id == seeded_team.id
    assert fetched.name == seeded_team.name
    assert fetched.members is not None


def test_get_all(client: Albert, seeded_team: Team):
    """Test listing teams with pagination and name filter."""
    by_name = list(client.teams.get_all(name=seeded_team.name, exact_match=True))
    assert len(by_name) == 1
    assert by_name[0].id == seeded_team.id


def test_update(client: Albert, seed_prefix: str, static_user: User, second_user: User):
    """Test update: rename, add/remove via members list."""
    team = client.teams.create(name=f"{seed_prefix}-update")
    try:
        # Add second_user via add_users (consistent, no ACL propagation delay)
        team = client.teams.add_users(
            id=team.id,
            members=[TeamMember(id=second_user.id, role="TeamViewer")],
        )

        # Rename + remove member in one update call
        team.name = f"{seed_prefix}-update-renamed"
        team.members = [m for m in team.members if m.id != second_user.id]
        client.teams.update(team=team)
        updated = _assert_member_absent(client, team.id, second_user.id)
        assert updated.name == f"{seed_prefix}-update-renamed"

        # Add member back via members list
        updated.members.append(TeamMember(id=second_user.id, role="TeamViewer"))
        client.teams.update(team=updated)
        _assert_member_present(client, team.id, second_user.id)
    finally:
        with suppress(Exception):
            client.teams.delete(id=team.id)


def test_add_users(client: Albert, seed_prefix: str, second_user: User):
    """Test adding users and duplicate detection."""
    team = client.teams.create(name=f"{seed_prefix}-add-users")
    try:
        # Add a user (creator is already a member, so add second_user)
        team = client.teams.add_users(
            id=team.id,
            members=[TeamMember(id=second_user.id, role="TeamViewer")],
        )
        assert second_user.id in [m.id for m in team.members or []]

        # Duplicate raises
        with pytest.raises(AlbertException, match="already in team"):
            client.teams.add_users(
                id=team.id,
                members=[TeamMember(id=second_user.id, role="TeamOwner")],
            )
    finally:
        with suppress(Exception):
            client.teams.delete(id=team.id)


def test_remove_users(client: Albert, seed_prefix: str, second_user: User):
    """Test removing users and non-member detection."""
    team = client.teams.create(name=f"{seed_prefix}-remove-users")
    try:
        # Add second_user explicitly so they're in the ACL
        client.teams.add_users(
            id=team.id,
            members=[TeamMember(id=second_user.id, role="TeamViewer")],
        )

        # Remove the viewer (creator/owner stays)
        team = client.teams.remove_users(id=team.id, users=[second_user.id])
        assert second_user.id not in [m.id for m in team.members or []]

        # Non-member raises
        with pytest.raises(AlbertException, match="None of the provided users"):
            client.teams.remove_users(id=team.id, users=[second_user.id])
    finally:
        with suppress(Exception):
            client.teams.delete(id=team.id)


def test_delete(client: Albert, seed_prefix: str):
    """Test deleting a team."""
    team = client.teams.create(name=f"{seed_prefix}-delete")
    client.teams.delete(id=team.id)
    with pytest.raises(NotFoundError):
        client.teams.get_by_id(id=team.id)
