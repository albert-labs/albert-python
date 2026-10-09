"""Change over time: grants, revokes, class changes, team removal, role downgrade.

Each change is applied, then the effect is polled for up to ``PROPAGATION_S`` seconds.
The measured delay is recorded in the report; not taking effect within the window is a
finding.
"""

import time

import pytest

from albert.core.shared.models.base import EntityLink
from albert.resources.projects import Project, ProjectClass
from albert.resources.teams import TeamMember
from tests.acl.checks import check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import Response, call
from tests.acl.world import grant, revoke

PROPAGATION_S = 90.0


def _wait_for(client, path, want_ok: bool) -> tuple[Response, float]:
    start = time.monotonic()
    while True:
        resp = call(client, "GET", path)
        ok = 200 <= resp.status < 300
        if ok == want_ok or time.monotonic() - start > PROPAGATION_S:
            return resp, round(time.monotonic() - start, 1)
        time.sleep(3)


@pytest.fixture(scope="module")
def project_user(switcher):
    return switcher.use(
        "broad-records",
        [
            "ProjectsFullAccess",
            "FormulaFullAccess",
            "TasksFullAccess",
            "InventoryFullAccess",
            "NotesFullAccess",
            "ReportsFullAccess",
            "PricingFullAccess",
        ],
    )


def test_revoke_takes_effect_on_children(request, admin, project_user, user_ids, world):
    """Test that after revoking a project grant, a child task becomes unreadable."""
    tree = world.projects[AccessClass.PRIVATE]
    pid, tid = tree.ids[Kind.PROJECT], tree.ids[Kind.GENERAL_TASK]
    grant(admin, pid, user_ids["userA"], "ProjectEditor")
    _wait_for(project_user, f"/api/v3/tasks/{tid}", want_ok=True)
    revoke(admin, pid, user_ids["userA"])
    resp, delay = _wait_for(project_user, f"/api/v3/tasks/{tid}", want_ok=False)
    check(
        request,
        scenario="change:revoke",
        subject="ProjectEditor",
        action="general_task.read_after_revoke",
        expect=Expect.DENY,
        resp=resp,
        detail=f"delay={delay}s",
    )


def test_team_removal_revokes_access(request, admin, project_user, user_ids, world):
    """Test that removing userA from a team granted on a project removes their access."""
    tree = world.projects[AccessClass.CONFIDENTIAL]
    pid = tree.ids[Kind.PROJECT]
    team = admin.teams.create(
        name=f"{world.prefix}-team",
        members=[TeamMember(id=user_ids["userA"], role="TeamViewer")],
    )
    try:
        grant(admin, pid, team.id, "ProjectViewer")
        resp, _ = _wait_for(project_user, f"/api/v3/projects/{pid}", want_ok=True)
        check(
            request,
            scenario="change:team",
            subject="team ProjectViewer",
            action="project.read_via_team",
            expect=Expect.ALLOW,
            resp=resp,
        )
        admin.teams.remove_users(id=team.id, users=[user_ids["userA"]])
        resp, delay = _wait_for(project_user, f"/api/v3/projects/{pid}", want_ok=False)
        check(
            request,
            scenario="change:team",
            subject="team ProjectViewer",
            action="project.read_after_team_removal",
            expect=Expect.DENY,
            resp=resp,
            detail=f"delay={delay}s",
        )
    finally:
        revoke(admin, pid, team.id)
        admin.teams.delete(id=team.id)


def test_role_downgrade_removes_policy(request, admin, switcher, world):
    """Test that swapping userA from Projects Full to Projects View blocks project edits."""
    pid = world.projects[AccessClass.SHARED].ids[Kind.PROJECT]
    switcher.use("ProjectsFullAccess", ["ProjectsFullAccess"])
    user = switcher.use("ProjectsViewAccess", ["ProjectsViewAccess"])
    body = {"data": [{"operation": "update", "attribute": "description", "newValue": "acl-dg"}]}
    start = time.monotonic()
    while True:
        resp = call(user, "PATCH", f"/api/v3/projects/{pid}", json=body)
        if resp.status in (403, 404) or time.monotonic() - start > PROPAGATION_S:
            break
        time.sleep(5)
    check(
        request,
        scenario="change:role_downgrade",
        subject="ProjectsViewAccess",
        action="project.update_after_downgrade",
        expect=Expect.DENY,
        resp=resp,
        detail=f"delay={round(time.monotonic() - start, 1)}s",
    )


def test_class_change_to_confidential_hides_project(request, admin, user_b, world):
    """Test that changing a shared project to confidential hides it from a no-grant user."""
    project = admin.projects.create(
        project=Project(
            description=f"{world.prefix} class-change",
            locations=[EntityLink(id=world.location.id)],
            project_class=ProjectClass.SHARED,
        )
    )
    try:
        path = f"/api/v3/projects/{project.id}"
        change = call(
            admin,
            "PATCH",
            path,
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "class",
                        "oldValue": "shared",
                        "newValue": "confidential",
                    }
                ]
            },
        )
        if change.status >= 300:
            pytest.fail(
                f"harness error: class change rejected for admin: {change.status}", pytrace=False
            )
        resp, delay = _wait_for(user_b, path, want_ok=False)
        check(
            request,
            scenario="change:class",
            subject="class shared->confidential",
            action="project.read_after_class_change",
            expect=Expect.DENY,
            resp=resp,
            detail=f"delay={delay}s",
        )
    finally:
        call(admin, "DELETE", f"/api/v3/projects/{project.id}")
