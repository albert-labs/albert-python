"""Children follow their parent (PLSV-827).

If a caller cannot GET a record, it must not GET the record's notes or attachments by their
own ids, whether the file hangs off the record directly or through a note. Children are
fetched with no ``parentId``: the parent must be resolved from the record, not the request.

Each parent seeded in ``world.py`` carries four children: a plain note, a note wrapping an
attachment, the attachment inside that note, and a direct attachment.
"""

import pytest

from albert import Albert
from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import call
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
)

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
