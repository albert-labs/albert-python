"""Ordinary mistakes a real user makes: stale ids, deleted records, copying between
records, and acting on a record by id after access was never granted.
"""

import pytest

from albert.core.shared.models.base import EntityLink
from albert.resources.projects import Project, ProjectClass
from tests.acl.checks import check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import call


def test_deleted_project_is_not_readable(request, admin, user_b, world):
    """Test that a deleted shared project is no longer readable by id."""
    project = admin.projects.create(
        project=Project(
            description=f"{world.prefix} to-delete",
            locations=[EntityLink(id=world.location.id)],
            project_class=ProjectClass.SHARED,
        )
    )
    call(admin, "DELETE", f"/api/v3/projects/{project.id}")
    resp = call(user_b, "GET", f"/api/v3/projects/{project.id}")
    check(
        request,
        scenario="mistake:deleted",
        subject="class=shared",
        action="project.read_deleted",
        expect=Expect.DENY,
        resp=resp,
    )


@pytest.mark.parametrize("kind", [Kind.TASK_CHILD, Kind.INVENTORY_CHILD])
def test_note_edit_on_hidden_parent(request, user_b, world, kind):
    """Test that a user cannot edit a note whose confidential parent they cannot see."""
    tree = (world.inventories if kind is Kind.INVENTORY_CHILD else world.projects)[
        AccessClass.CONFIDENTIAL
    ]
    resp = call(
        user_b,
        "PATCH",
        f"/api/v3/notes/{tree.ids[kind]}",
        json={"data": [{"operation": "update", "attribute": "note", "newValue": "acl-mistake"}]},
    )
    check(
        request,
        scenario="mistake:hidden_parent",
        subject="no-grant",
        action=f"{kind.value}.update",
        expect=Expect.DENY,
        resp=resp,
    )


def test_note_reparent_into_hidden_record(request, admin, user_b, world):
    """Test that a user cannot move their note under a confidential record via parentId."""
    shared_task = world.projects[AccessClass.SHARED].ids[Kind.GENERAL_TASK]
    hidden_task = world.projects[AccessClass.CONFIDENTIAL].ids[Kind.GENERAL_TASK]
    created = call(user_b, "POST", "/api/v3/notes", json={"parentId": shared_task, "note": "acl"})
    if not 200 <= created.status < 300:
        pytest.fail(
            f"harness error: userB cannot create note on shared task: {created.status}",
            pytrace=False,
        )
    nid = created.body.get("albertId")
    try:
        resp = call(
            user_b,
            "PATCH",
            f"/api/v3/notes/{nid}",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "parentId",
                        "oldValue": shared_task,
                        "newValue": hidden_task,
                    }
                ]
            },
        )
        check(
            request,
            scenario="mistake:reparent",
            subject="no-grant",
            action="note.reparent_into_confidential",
            expect=Expect.DENY,
            resp=resp,
        )
    finally:
        call(admin, "DELETE", f"/api/v3/notes/{nid}")


def test_notebook_copy_from_hidden_project(request, admin, user_b, world):
    """Test that a user cannot copy a confidential project's notebook into a shared project."""
    src = world.projects[AccessClass.CONFIDENTIAL].ids[Kind.PROJECT_CHILD]
    dest = world.projects[AccessClass.SHARED].ids[Kind.PROJECT]
    resp = call(
        user_b,
        "POST",
        "/api/v3/notebooks/copy",
        params={"type": "Project", "parentId": dest},
        json={"id": src, "parentId": dest},
    )
    try:
        check(
            request,
            scenario="mistake:copy",
            subject="no-grant",
            action="notebook.copy_from_confidential",
            expect=Expect.DENY,
            resp=resp,
        )
    finally:
        if 200 <= resp.status < 300 and isinstance(resp.body, dict) and resp.body.get("albertId"):
            call(admin, "DELETE", f"/api/v3/notebooks/{resp.body['albertId']}")
