import pytest

from albert.resources.projects import Project


@pytest.mark.parametrize(
    "raw_status, expected",
    [
        ("ACTIVE", "active"),
        ("Active", "active"),
        ("closed - success", "closed - success"),
        (None, None),
    ],
)
def test_project_status_validator_lowercases_strings(raw_status, expected):
    """Test Project.status lowercases string input and passes through non-string values."""
    project = Project(description="Test project", status=raw_status)
    assert project.status == expected


def test_project_status_excluded_from_dump():
    """Test Project.status stays out of the wire payload despite being settable."""
    project = Project(description="Test project", status="Active")
    dumped = project.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert "status" not in dumped
