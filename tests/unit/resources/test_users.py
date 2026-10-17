from albert.resources.users import User


def test_user_parses_cleared_metadata_field():
    """Test that a user whose custom metadata field was cleared to null parses."""
    user = User.model_validate(
        {
            "albertId": "USR2414",
            "name": "Test User",
            "email": "test.user@example.com",
            "status": "active",
            "Metadata": {"SBU": None, "Region": "EMEA"},
        }
    )

    assert user.metadata == {"SBU": None, "Region": "EMEA"}
