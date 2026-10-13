"""Offline checks for the ACL suite's oracle and contracts (no network)."""

import re
from pathlib import Path

import pytest

from tests.acl.contract.fgc import (
    CONTENT_PATHS,
    DIRECT_PATHS,
    INVENTORY_LEVELS,
    POLICY_TASKS,
    PROJECT_LEVELS,
    AccessClass,
    Kind,
    ReadPath,
    class_expect,
)
from tests.acl.contract.model import Expect, Module, Verb
from tests.acl.contract.policies import BY_ID, POLICIES
from tests.acl.oracle import Observation, Verdict, judge

ACL_DIR = Path(__file__).parents[2] / "acl"


@pytest.mark.parametrize(
    ("expect", "status", "visible", "verdict"),
    [
        (Expect.DENY, 403, None, Verdict.PASS),
        (Expect.DENY, 404, None, Verdict.PASS),
        (Expect.DENY, 200, None, Verdict.LEAK),
        (Expect.DENY, 200, False, Verdict.PASS),
        (Expect.DENY, 200, True, Verdict.LEAK),
        (Expect.ALLOW, 200, None, Verdict.PASS),
        (Expect.ALLOW, 200, False, Verdict.OVER_RESTRICTED),
        (Expect.ALLOW, 403, None, Verdict.OVER_RESTRICTED),
        (Expect.ALLOW, 500, None, Verdict.SERVER_ERROR),
        (Expect.DENY, 502, None, Verdict.SERVER_ERROR),
        (Expect.UNDECIDED, 500, None, Verdict.SERVER_ERROR),
        (Expect.UNDECIDED, 200, None, Verdict.UNDECIDED),
        (Expect.DENY, 400, None, Verdict.INCONCLUSIVE),
        (Expect.ALLOW, 409, None, Verdict.INCONCLUSIVE),
    ],
)
def test_judge(expect, status, visible, verdict):
    """Test that the oracle maps each status/visibility pair to the documented verdict."""
    assert judge(expect, Observation(status, visible)) is verdict


def test_policy_ids_unique():
    """Test that every contracted policy id appears once."""
    assert len(BY_ID) == len(POLICIES)


def test_no_edit_policy_shares():
    """Test that no Edit/View policy grants share (sharing needs a Full policy)."""
    for p in POLICIES:
        if "Full" in p.id or p.id == "AskAlbertSkillsFullAccess":
            continue
        for module, verbs in p.grants.items():
            assert Verb.SHARE not in verbs, f"{p.id} grants share on {module}"


@pytest.mark.parametrize("module", [Module.CAS, Module.UNITS, Module.LISTS, Module.LOCATIONS])
def test_interim_admin_only_delete(module):
    """Test that no policy grants delete on CAS/Units/Lists/Locations (admin-only, interim)."""
    for p in POLICIES:
        assert p.expect(module, Verb.DELETE) is not Expect.ALLOW, p.id


def test_no_policy_deletes_projects():
    """Test that project delete is admin-only in the contract."""
    for p in POLICIES:
        assert p.expect(Module.PROJECTS, Verb.DELETE) is Expect.DENY, p.id


def test_only_owner_levels_share():
    """Test that only owner FGC levels may share a record."""
    for lv in (*PROJECT_LEVELS.values(), *INVENTORY_LEVELS.values()):
        for kind in (Kind.PROJECT, Kind.INVENTORY):
            if lv.expect(kind, Verb.SHARE) is Expect.ALLOW:
                assert lv.level in ("ProjectOwner", "InventoryOwner"), lv.level


def test_property_task_level_is_not_a_project_level():
    """Test that ProjectPropertyTask is not contracted as a project level (it follows the
    property-task policies)."""
    assert "ProjectPropertyTask" not in PROJECT_LEVELS


def test_project_levels_do_not_govern_policy_tasks():
    """Test that no project FGC level has cells for general or property tasks."""
    for lv in PROJECT_LEVELS.values():
        assert not POLICY_TASKS & (lv.grants.keys() | lv.undecided.keys()), lv.level


def test_strict_viewer_is_read_only():
    """Test that ProjectStrictViewer grants nothing beyond read (and report create)."""
    lv = PROJECT_LEVELS["ProjectStrictViewer"]
    for kind, verbs in lv.grants.items():
        extra = verbs - {Verb.READ} - ({Verb.CREATE} if kind is Kind.REPORT else set())
        assert not extra, f"{kind}: {extra}"


def test_viewer_cannot_edit_project_or_formula():
    """Test that ProjectViewer (legacy technician) cannot edit the project or its formulas."""
    lv = PROJECT_LEVELS["ProjectViewer"]
    assert lv.expect(Kind.PROJECT, Verb.UPDATE) is Expect.DENY
    assert lv.expect(Kind.FORMULA, Verb.UPDATE) is Expect.DENY
    assert lv.expect(Kind.LOT, Verb.UPDATE) is Expect.ALLOW


def test_confidential_never_readable_without_grant():
    """Test that the class contract never lets a no-grant user read a confidential record."""
    for path in ReadPath:
        assert class_expect(AccessClass.CONFIDENTIAL, Verb.READ, path) is Expect.DENY


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (path, Expect.DENY if path in DIRECT_PATHS | CONTENT_PATHS else Expect.ALLOW)
        for path in ReadPath
    ],
    ids=lambda v: getattr(v, "value", v),
)
def test_private_listable_but_not_directly_readable(path, expected):
    """Test that a private record is visible on list paths but denied on direct and contents
    reads (PLSV-827)."""
    assert class_expect(AccessClass.PRIVATE, Verb.READ, path) is expected


def test_private_write_denied_without_grant():
    """Test that a no-grant user may never update a private record."""
    assert class_expect(AccessClass.PRIVATE, Verb.UPDATE, ReadPath.SEARCH_GET) is Expect.DENY


BANNED = re.compile(
    r"operationIds?|decision\.js|checkacl|checkrole|fgc\.js|dbs-acl|mid-acl|getOperationIds"
)


def test_acl_suite_never_reads_backend_oracle():
    """Test that no file in tests/acl derives expectations from backend code or opIds."""
    offenders = []
    for path in ACL_DIR.rglob("*.py"):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if BANNED.search(line):
                offenders.append(f"{path.relative_to(ACL_DIR)}:{n}: {line.strip()}")
    assert not offenders, "backend-derived oracle referenced:\n" + "\n".join(offenders)
