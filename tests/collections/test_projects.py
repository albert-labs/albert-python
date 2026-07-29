from contextlib import suppress

import pytest

from albert.client import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import NotFoundError
from albert.resources.attachments import Attachment
from albert.resources.projects import DocumentSearchItem, Project, ProjectSearchItem
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("projects")


def assert_valid_project_items(returned_list: list, entity_type: type = Project):
    """Assert that project items are valid and correctly typed."""
    assert returned_list, "Expected at least one project"
    for item in returned_list[:50]:
        assert isinstance(item, entity_type)
        assert isinstance(item.description, str)
        assert isinstance(item.id, str) and item.id


def test_project_get_all(client: Albert):
    """Test get_all returns hydrated Project items."""
    project_list = list(client.projects.get_all(max_items=10))
    assert_valid_project_items(project_list, Project)


def test_project_search_basic(client: Albert):
    """Test search returns ProjectSearchItem items."""
    project_list = list(client.projects.search(max_items=10))
    assert_valid_project_items(project_list, ProjectSearchItem)


def test_project_search_paged(client: Albert):
    """Test search with a small page size."""
    short_lists = list(client.projects.search(max_items=10))
    assert_valid_project_items(short_lists, ProjectSearchItem)


def test_project_search_filtered(client: Albert):
    """Test search with status filter."""
    advanced_list = list(client.projects.search(status=["Active"], max_items=10))
    assert_valid_project_items(advanced_list, ProjectSearchItem)


def test_hydrate_project(client: Albert, seed_prefix: str, seeded_projects: list[Project]):
    # Filter to this worker's seeds: text search is fuzzy (tokenized) and can rank
    # unrelated projects the client has no ACL access to hydrate
    seeded_ids = {p.id for p in seeded_projects}
    projects = poll_until(
        lambda: [
            p
            for p in client.projects.search(text=seed_prefix, max_items=100)
            if p.id in seeded_ids
        ]
    )
    assert projects, "Expected at least one project in search results"

    for project in projects:
        hydrated = project.hydrate()
        # identity checks
        assert hydrated.id == project.id
        assert hydrated.description == project.description


def test_project_document_search(
    client: Albert,
    seeded_projects: list[Project],
    seeded_project_document: Attachment,
):
    """Test document_search returns DocumentSearchItem items for a project."""
    project_id = seeded_projects[0].id
    documents = list(
        client.projects.document_search(
            linked_to=project_id,
            sort_by="createdAt",
            max_items=25,
        )
    )
    assert documents, "Expected at least one document"
    for doc in documents:
        assert isinstance(doc, DocumentSearchItem)
        assert doc.id is not None


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


def test_update_project(seeded_locations, client: Albert, seed_prefix: str):
    # Update a private project so shared seeded projects stay intact
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - Project to Update",
            locations=[EntityLink(id=seeded_locations[1].id)],
        )
    )
    try:
        project.grid = "PD"
        updated = client.projects.update(project=project)
        assert updated.id == project.id
    finally:
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)


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
