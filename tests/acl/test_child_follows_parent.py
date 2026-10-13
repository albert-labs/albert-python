"""Children follow their parent (PLSV-827).

If a caller cannot GET a record, it must not GET the record's notes or attachments by their
own ids, whether the file hangs off the record directly or through a note. Children are
fetched with no ``parentId``: the parent must be resolved from the record, not the request.

Each parent seeded in ``world.py`` carries four children: a plain note, a note wrapping an
attachment, the attachment inside that note, and a direct attachment.
"""

import pytest

from albert import Albert
from albert.exceptions import AlbertHTTPError
from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import Response, call
from tests.acl.oracle import DENY_STATUSES
from tests.acl.report import Row, record
from tests.acl.world import (
    ATTACHMENT,
    ATTACHMENT_NOTE,
    CHILD_TYPES,
    INVENTORY_CLASSES,
    NOTE,
    NOTE_ATTACHMENT,
    PROJECT_CLASSES,
    _seed_children,
    grant,
    revoke,
)
from tests.utils.wait import poll_until

PARENT_PATH = {
    Kind.INVENTORY: "/api/v3/inventories/{}",
    Kind.FORMULA: "/api/v3/inventories/{}",
    Kind.GENERAL_TASK: "/api/v3/tasks/{}",
    Kind.BATCH_TASK: "/api/v3/tasks/{}",
    Kind.PROJECT_CHILD: "/api/v3/notebooks/{}",
}

CHILD_PATH = {
    NOTE: "/api/v3/notes/{}",
    ATTACHMENT_NOTE: "/api/v3/notes/{}",
    NOTE_ATTACHMENT: "/api/v3/attachments/{}",
    ATTACHMENT: "/api/v3/attachments/{}",
}

SUBJECTS = {"no-grant": "user_b", "views-no-tasks": "views_no_tasks_user"}

VIEW_POLICIES = ["ProjectsViewAccess", "FormulaViewAccess", "InventoryViewAccess"]


@pytest.fixture(scope="module")
def views_no_tasks_user(switcher) -> Albert:
    """userA with project, formula and inventory view but no Tasks policy."""
    return switcher.use("views-no-tasks", VIEW_POLICIES)


def _parents():
    for cls in INVENTORY_CLASSES:
        yield Kind.INVENTORY, cls
    for kind in (Kind.FORMULA, Kind.GENERAL_TASK, Kind.BATCH_TASK, Kind.PROJECT_CHILD):
        for cls in PROJECT_CLASSES:
            yield kind, cls


def _tree(world, kind, cls):
    return (world.inventories if kind is Kind.INVENTORY else world.projects)[cls]


def _cases():
    for subject in SUBJECTS:
        for kind, cls in _parents():
            for child in CHILD_TYPES:
                yield pytest.param(
                    kind, cls, child, subject, id=f"{subject}-{kind.value}-{cls.value}-{child}"
                )


@pytest.mark.parametrize(("kind", "cls", "child", "subject"), list(_cases()))
def test_child_denied_when_parent_denied(request, admin, world, kind, cls, child, subject):
    """Test that a child note or attachment is unreadable by id whenever its parent is
    (PLSV-827). A readable parent is recorded without asserting on the child."""
    tree = _tree(world, kind, cls)
    parent_path = PARENT_PATH[kind].format(tree.ids[kind])
    child_path = CHILD_PATH[child].format(tree.children[kind][child])
    admin_control(call(admin, "GET", parent_path), f"{kind.value}.read")
    admin_control(call(admin, "GET", child_path), f"{kind.value}.{child}.read")

    user = request.getfixturevalue(SUBJECTS[subject])
    parent = call(user, "GET", parent_path)
    child_resp = call(user, "GET", child_path)
    scenario = "PLSV-827:child_follows_parent"
    action = f"{kind.value}[{cls.value}].{child}.read"
    if parent.status in DENY_STATUSES:
        check(
            request,
            scenario=scenario,
            subject=subject,
            action=action,
            expect=Expect.DENY,
            resp=child_resp,
            detail=f"parent {parent.status}",
        )
    else:
        record(
            request,
            Row(
                scenario,
                subject,
                action,
                "observe",
                child_resp.status,
                "observed",
                f"parent {parent.status}",
            ),
        )


@pytest.mark.parametrize("child", [NOTE_ATTACHMENT, ATTACHMENT])
@pytest.mark.parametrize("kind", [Kind.PROJECT_CHILD, Kind.BATCH_TASK], ids=lambda k: k.value)
@pytest.mark.parametrize(
    "cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL], ids=lambda c: c.value
)
def test_hidden_project_attachment_by_id_denied(request, admin, user_b, world, cls, kind, child):
    """Test that a no-grant user cannot fetch a private/confidential project's attachment by
    its id when no parentId is supplied (PLSV-827)."""
    path = CHILD_PATH[child].format(world.projects[cls].children[kind][child])
    admin_control(call(admin, "GET", path), f"{kind.value}.{child}.read")
    check(
        request,
        scenario="PLSV-827:attachment_by_id",
        subject="no-grant",
        action=f"{kind.value}[{cls.value}].{child}.get_by_id",
        expect=Expect.DENY,
        resp=call(user_b, "GET", path),
    )


# The delete subject holds the policies that grant note and attachment delete, so a refusal on
# these parents comes from project membership; ``test_member_can_delete_children`` proves it.
DELETE_POLICIES = ["ProjectsViewAccess", "TasksFullAccess", "InventoryViewAccess"]
DELETE_SUBJECT = "task-editor"
DELETE_PARENTS = [
    (Kind.BATCH_TASK, AccessClass.PRIVATE),
    (Kind.PROJECT_CHILD, AccessClass.PRIVATE),
    (Kind.BATCH_TASK, AccessClass.CONFIDENTIAL),
    (Kind.PROJECT_CHILD, AccessClass.CONFIDENTIAL),
]


@pytest.fixture(scope="module")
def task_editor(switcher) -> Albert:
    """userA with project view and full task access, and no grant on any seeded project."""
    return switcher.use("delete-task-full", DELETE_POLICIES)


def _sdk_delete(client: Albert, child: str, rid: str) -> Response:
    """Delete through the SDK (``notes.delete`` / ``attachments.delete``); a refusal becomes
    the error's status so the oracle can judge it."""
    collection = (
        client.notes if CHILD_PATH[child].startswith("/api/v3/notes") else client.attachments
    )
    try:
        collection.delete(id=rid)
    except AlbertHTTPError as err:
        if err.response is None:
            raise
        return Response(status=err.response.status_code, body=err.response.text)
    return Response(status=204, body=None)


def _delete_cases():
    for kind, cls in DELETE_PARENTS:
        for child in CHILD_TYPES:
            yield pytest.param(kind, cls, child, id=f"{kind.value}-{cls.value}-{child}")


def _wait_readable(client: Albert, path: str, readable: bool) -> Response:
    return poll_until(
        lambda: [call(client, "GET", path)],
        predicate=lambda r: (200 <= r[0].status < 300) == readable,
        timeout=90,
        interval=3,
    )[0]


class TestMemberCanDeleteChildren:
    """One ProjectEditor grant for every case, so a revoke from one case cannot race the
    next case's grant."""

    @pytest.fixture(scope="class")
    def member_grant(self, admin, user_ids, world):
        pid = world.projects[AccessClass.PRIVATE].ids[Kind.PROJECT]
        grant(admin, pid, user_ids["userA"], "ProjectEditor")
        yield
        revoke(admin, pid, user_ids["userA"])

    @pytest.mark.parametrize("child", CHILD_TYPES)
    @pytest.mark.parametrize("kind", [Kind.BATCH_TASK, Kind.PROJECT_CHILD], ids=lambda k: k.value)
    def test_member_can_delete_children(
        self, request, admin, task_editor, world, member_grant, kind, child
    ):
        """Test that the delete subject, as a member (ProjectEditor) of the private project,
        can delete its notes and attachments, so its refusals as a non-member are meaningful."""
        tree = world.projects[AccessClass.PRIVATE]
        seeded = _seed_children(admin, tree.ids[kind], tree.canary)
        child_path = CHILD_PATH[child].format(seeded[child])
        try:
            _wait_readable(task_editor, PARENT_PATH[kind].format(tree.ids[kind]), True)
            _wait_readable(task_editor, child_path, True)
            check(
                request,
                scenario="PLSV-827:child_delete",
                subject=f"{DELETE_SUBJECT}+ProjectEditor",
                action=f"{kind.value}[private].{child}.delete",
                expect=Expect.ALLOW,
                resp=_sdk_delete(task_editor, child, seeded[child]),
            )
        finally:
            for other, rid in seeded.items():
                _sdk_delete(admin, other, rid)


@pytest.mark.parametrize(("kind", "cls", "child"), list(_delete_cases()))
def test_child_delete_denied_when_parent_denied(
    request, admin, task_editor, world, kind, cls, child
):
    """Test that a task editor who is not a member of a private/confidential project cannot
    delete its notes or attachments by their own ids (PLSV-827). Each case seeds fresh
    children, so a leak deletes nothing shared."""
    tree = _tree(world, kind, cls)
    parent_path = PARENT_PATH[kind].format(tree.ids[kind])
    admin_control(call(admin, "GET", parent_path), f"{kind.value}.read")
    seeded = _seed_children(admin, tree.ids[kind], tree.canary)
    child_path = CHILD_PATH[child].format(seeded[child])
    user = task_editor
    try:
        parent = _wait_readable(user, parent_path, False)
        if parent.status not in DENY_STATUSES:
            pytest.fail(
                f"harness error: {DELETE_SUBJECT} can read {kind.value}[{cls.value}] "
                f"({parent.status}); the delete probe needs a denied parent",
                pytrace=False,
            )
        resp = _sdk_delete(user, child, seeded[child])
        detail = f"parent {parent.status}"
        if 200 <= resp.status < 300:
            gone = call(admin, "GET", child_path).status == 404
            detail += "; record deleted" if gone else "; record still present"
        else:
            admin_control(_sdk_delete(admin, child, seeded[child]), f"{kind.value}.{child}.delete")
        check(
            request,
            scenario="PLSV-827:child_delete",
            subject=DELETE_SUBJECT,
            action=f"{kind.value}[{cls.value}].{child}.delete",
            expect=Expect.DENY,
            resp=resp,
            detail=detail,
        )
    finally:
        for other, rid in seeded.items():
            _sdk_delete(admin, other, rid)
