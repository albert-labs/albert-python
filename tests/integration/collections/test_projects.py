from contextlib import suppress

import pytest

from albert.client import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import NotFoundError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.attachments import Attachment
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.projects import (
    DocumentSearchItem,
    Project,
    ProjectSearchItem,
    ReferenceFormula,
    ReferenceFormulaType,
)
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
    attachment_id = seeded_project_document.id
    documents = poll_until(
        lambda: [
            doc
            for doc in client.projects.document_search(
                linked_to=project_id,
                sort_by="createdAt",
                max_items=25,
            )
            if doc.id == attachment_id
        ]
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


def test_update_project_acl(
    client: Albert,
    seeded_locations,
    seed_prefix: str,
):
    """Test updating a project's ACL via update()."""
    team = client.teams.create(name=f"{seed_prefix} - project ACL team")
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - ACL update project",
            locations=[EntityLink(id=seeded_locations[0].id)],
            acl=[ACL(id=team.id, fgc=AccessControlLevel.PROJECT_VIEWER)],
        )
    )
    try:
        fetched = client.projects.get_by_id(id=project.id)
        updated_acl = [
            ACL(
                id=entry.id,
                fgc=(
                    AccessControlLevel.PROJECT_STRICT_VIEWER if entry.id == team.id else entry.fgc
                ),
            )
            for entry in fetched.acl or []
        ]
        updated = client.projects.update(project=fetched.model_copy(update={"acl": updated_acl}))
        entry = next(entry for entry in updated.acl or [] if entry.id == team.id)
        assert entry.fgc == AccessControlLevel.PROJECT_STRICT_VIEWER
    finally:
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)
        with suppress(NotFoundError):
            client.teams.delete(id=team.id)


def test_update_project_acl_in_place(
    client: Albert,
    seeded_locations,
    seed_prefix: str,
):
    """Test in-place ACL edits trigger update without reassigning acl."""
    team = client.teams.create(name=f"{seed_prefix} - in-place ACL team")
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - in-place ACL project",
            locations=[EntityLink(id=seeded_locations[0].id)],
            acl=[ACL(id=team.id, fgc=AccessControlLevel.PROJECT_VIEWER)],
        )
    )
    try:
        fetched = client.projects.get_by_id(id=project.id)
        team_entry = next(entry for entry in fetched.acl or [] if entry.id == team.id)
        team_entry.fgc = AccessControlLevel.PROJECT_STRICT_VIEWER
        updated = client.projects.update(project=fetched)
        entry = next(entry for entry in updated.acl or [] if entry.id == team.id)
        assert entry.fgc == AccessControlLevel.PROJECT_STRICT_VIEWER
    finally:
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)
        with suppress(NotFoundError):
            client.teams.delete(id=team.id)


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


def test_reactivate_project(client: Albert, seeded_locations, seed_prefix: str):
    """Test reactivating a soft-deleted project restores access."""
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - Project to Reactivate",
            locations=[EntityLink(id=seeded_locations[1].id)],
        )
    )
    try:
        client.projects.delete(id=project.id)
        with pytest.raises(NotFoundError):
            client.projects.get_by_id(id=project.id)

        reactivated = client.projects.reactivate(id=project.id)
        assert reactivated.id == project.id
        assert reactivated.status == "active"
    finally:
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)


def test_reference_formulas_lifecycle(
    client: Albert,
    seed_prefix: str,
    seeded_locations,
):
    """Test full reference formula lifecycle: set, link, list, update, and delete."""
    host_project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - RF Host Project",
            locations=[EntityLink(id=seeded_locations[0].id)],
        )
    )
    source_project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - RF Source Project",
            locations=[EntityLink(id=seeded_locations[0].id)],
        )
    )
    formula_1 = None
    formula_2 = None

    try:
        worksheet = client.worksheets.setup_worksheet(project_id=host_project.id)
        sheet_id = worksheet.sheets[0].id

        formula_1 = client.inventory.create(
            inventory_item=InventoryItem(
                name=f"{seed_prefix} - RF Formula 1",
                category=InventoryCategory.FORMULAS,
                project_id=host_project.id,
            ),
            avoid_duplicates=False,
        )
        formula_2 = client.inventory.create(
            inventory_item=InventoryItem(
                name=f"{seed_prefix} - RF Formula 2",
                category=InventoryCategory.FORMULAS,
                project_id=source_project.id,
            ),
            avoid_duplicates=False,
        )

        # 1. Set in-project reference formula
        rf_in_project = client.projects.set_reference_formula(
            project_id=host_project.id,
            sheet_id=sheet_id,
            inventory_id=formula_1.id,
            reference_formula_type=ReferenceFormulaType.ORIGINAL,
        )
        assert isinstance(rf_in_project, ReferenceFormula)
        assert rf_in_project.project_id == host_project.id
        assert rf_in_project.sheet_id == sheet_id
        assert rf_in_project.inventory_id == formula_1.id
        assert rf_in_project.reference_formula_type == "Original"
        assert rf_in_project.is_external_formula is False

        # 2. Link cross-project reference formula
        rf_linked = client.projects.link_reference_formula(
            project_id=host_project.id,
            parent_project_id=source_project.id,
            inventory_id=formula_2.id,
            reference_formula_type=ReferenceFormulaType.CONTROL,
        )
        assert isinstance(rf_linked, ReferenceFormula)
        assert rf_linked.project_id == host_project.id
        assert rf_linked.sheet_id is None
        assert rf_linked.inventory_id == formula_2.id
        assert rf_linked.parent_project_id == source_project.id
        assert rf_linked.reference_formula_type == "Control"
        assert rf_linked.is_external_formula is True

        # 3. List all reference formulas for host project
        all_rf = list(client.projects.get_all_reference_formulas(project_id=host_project.id))
        all_inv_ids = {rf.inventory_id for rf in all_rf}
        assert formula_1.id in all_inv_ids
        assert formula_2.id in all_inv_ids

        # 4. List sheet-filtered reference formulas
        sheet_rf = list(
            client.projects.get_all_reference_formulas(
                project_id=host_project.id,
                sheet_id=sheet_id,
            )
        )
        sheet_inv_ids = {rf.inventory_id for rf in sheet_rf}
        assert formula_1.id in sheet_inv_ids
        assert formula_2.id not in sheet_inv_ids

        # 5. List linked-only reference formulas
        linked_rf = list(
            client.projects.get_all_reference_formulas(
                project_id=host_project.id,
                linked_only=True,
            )
        )
        linked_inv_ids = {rf.inventory_id for rf in linked_rf}
        assert formula_2.id in linked_inv_ids
        assert formula_1.id not in linked_inv_ids

        # 6. List tenant-wide reference formulas
        tenant_rf = list(client.projects.get_all_reference_formulas(max_items=5))
        assert isinstance(tenant_rf, list)

        # 7. Update in-project reference formula type (with expected_type)
        updated_in_project = client.projects.update_reference_formula_type(
            project_id=host_project.id,
            sheet_id=sheet_id,
            inventory_id=formula_1.id,
            reference_formula_type=ReferenceFormulaType.LEADING,
            expected_type=ReferenceFormulaType.ORIGINAL,
        )
        assert isinstance(updated_in_project, ReferenceFormula)
        assert updated_in_project.reference_formula_type == "Leading"

        # 8. Update linked reference formula type with custom string
        updated_linked = client.projects.update_reference_formula_type(
            project_id=host_project.id,
            inventory_id=formula_2.id,
            reference_formula_type="CustomBaseline",
        )
        assert isinstance(updated_linked, ReferenceFormula)
        assert updated_linked.reference_formula_type == "CustomBaseline"
        assert updated_linked.parent_project_id == source_project.id
        assert updated_linked.is_external_formula is True

        # 9. Delete in-project reference formula
        client.projects.delete_reference_formula(
            project_id=host_project.id,
            sheet_id=sheet_id,
            inventory_id=formula_1.id,
        )

        # 10. Delete linked reference formula
        client.projects.delete_reference_formula(
            project_id=host_project.id,
            inventory_id=formula_2.id,
        )

        # 11. Verify deletions
        post_delete_rf = list(
            client.projects.get_all_reference_formulas(project_id=host_project.id)
        )
        post_delete_inv_ids = {rf.inventory_id for rf in post_delete_rf}
        assert formula_1.id not in post_delete_inv_ids
        assert formula_2.id not in post_delete_inv_ids

    finally:
        if formula_1 is not None and formula_1.id:
            with suppress(Exception):
                client.inventory.delete(id=formula_1.id)
        if formula_2 is not None and formula_2.id:
            with suppress(Exception):
                client.inventory.delete(id=formula_2.id)
        with suppress(Exception):
            client.projects.delete(id=host_project.id)
        with suppress(Exception):
            client.projects.delete(id=source_project.id)
