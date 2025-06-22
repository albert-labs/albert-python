import pytest

from albert.client import Albert
from albert.core.models.common import EntityLink
from albert.exceptions import NotFoundError
from albert.resources.projects import Project, ProjectFilterParams


def assert_project_items(returned_list, limit=50):
    found = False
    for i, project in enumerate(returned_list):
        if i == limit:  # Limit to checking first 50 projects
            break
        assert isinstance(project, Project)
        assert isinstance(project.description, str)
        assert isinstance(project.id, str)
        assert project.id is not None
        found = True
    assert found


def test_get_all_projects(client: Albert):
    project_list = client.projects.get_all()
    assert_project_items(project_list)


def test_search_projects(client: Albert):
    project_list = client.projects.search()
    assert_project_items(project_list)

    params = ProjectFilterParams(limit=5)
    short_lists = client.projects.search(params=params)
    assert_project_items(short_lists, limit=7)

    params = ProjectFilterParams(limit=2, status=["Active"])
    advanced_list = client.projects.search(params=params)
    assert_project_items(advanced_list, limit=2)


def test_get_by_id(client: Albert, seeded_projects: list[Project]):
    # Get the first seeded project by ID
    seeded_project = seeded_projects[0]
    fetched_project = client.projects.get_by_id(id=seeded_project.id)

    assert isinstance(fetched_project, Project)
    assert fetched_project.id == seeded_project.id
    assert fetched_project.description == seeded_project.description


def test_create_project(client: Albert, seeded_locations):
    # Create a new project
    new_project = Project(
        description="A basic development project.",
        locations=[EntityLink(id=seeded_locations[0].id)],
    )

    created_project = client.projects.create(project=new_project)
    assert isinstance(created_project, Project)
    assert isinstance(created_project.id, str)
    assert created_project.description == "A basic development project."

    # Clean up
    client.projects.delete(id=created_project.id)


def test_update_project(seeded_projects, client: Albert):
    seeded_projects[1].grid = "PD"
    updated = client.projects.update(project=seeded_projects[1])
    assert updated.id == seeded_projects[1].id


def test_delete_project(client: Albert, seeded_locations):
    # Create a new project to delete
    new_project = Project(
        description="Project to Delete",
        # acls=[],
        locations=[EntityLink(id=seeded_locations[1].id)],
    )

    created_project = client.projects.create(project=new_project)
    assert isinstance(created_project, Project)

    # Now delete the project
    client.projects.delete(id=created_project.id)

    # Try to fetch the project, should return None or not found
    with pytest.raises(NotFoundError):
        client.projects.get_by_id(id=created_project.id)
