"""Fast ACL smoke check through the SDK, in about two minutes.

    uv run python -m tests.acl.quick_check

Who acts (nobody's role is changed):
- admin: seeds records and runs every positive control.
- userA (standard, Full Access role): a project member via a temporary ProjectEditor grant.
- userB (standard, every policy): an outsider with no grant, or named on a single
  inventory item through a temporary InventoryViewer/InventoryOwner grant.

Sections:
1. Project class rules: a project's formula, the formula's lot, note and the file on that
   note, read and edited by a member and an outsider, for each project class.
2. A confidential raw material: the item, its lot, its note and the file on that note
   must be hidden from anyone not named on the item. Formulas have no access of their own
   (they follow their project), so they are covered by section 1 only.
3. Bypass routes: other SDK calls an outsider might use to reach hidden records.

Records the checks write to or delete are created fresh each run and removed at the end.
Long-lived projects and formulas come from ``static_docs.py``. Exits 1 on any failure.
Known gaps (``KNOWN_GAPS``: lot read inheritance, and outsider edits of a shared
project's formula and its notes) are shown with ``~`` and listed separately; they do not
fail the run.
"""

import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.companies import Company
from albert.resources.inventory import InventoryCategory, InventoryItem, InventoryUnitCategory
from albert.resources.locations import Location
from albert.resources.lots import Lot
from albert.resources.notebooks import NotebookCopyInfo, NotebookCopyType
from albert.resources.storage_locations import StorageLocation
from tests.acl.contract.fgc import AccessClass
from tests.acl.identities import base_url, load_identity, user_id
from tests.acl.static_docs import StaticDoc, ensure_static_doc, ensure_static_formula
from tests.acl.world import (
    ATTACHMENT,
    ATTACHMENT_NOTE,
    NOTE,
    NOTE_ATTACHMENT,
    _seed_children,
    grant,
    revoke,
)

PREFIX = "SDK-ACL-quick"
# Accepted platform limitations, keyed by row name (every column) or (row, column).
# Mismatches on these cells are reported as known gaps and do not fail the run.
LOT_GAP = "lot reads don't inherit the inventory's access (accepted platform limitation)"
SHARED_EDIT_GAP = (
    "outsiders can't edit a shared project's formula or its notes without a grant "
    "(accepted platform limitation)"
)
KNOWN_GAPS: dict[str | tuple[str, str], str] = {
    ("Edit formula", "shared out"): SHARED_EDIT_GAP,
    ("Edit formula's note", "shared out"): SHARED_EDIT_GAP,
    "Read formula's lot": LOT_GAP,
    "Confidential raw material: its lot": LOT_GAP,
    "Bulk-get its lot next to a shared lot": LOT_GAP,
}
PROJECT_CLASSES = (
    AccessClass.CONFIDENTIAL,
    AccessClass.PRIVATE,
    AccessClass.RESTRICTED,
    AccessClass.SHARED,
)
# (read, edit) by ID for a standard user outside the project (Explicit Named Access spec):
# shared is implicit all; restricted is implicit read, explicit edit; private is implicit
# list only, explicit read and edit; confidential is explicit all.
OUTSIDER_RULES = {
    AccessClass.CONFIDENTIAL: (False, False),
    AccessClass.PRIVATE: (False, False),
    AccessClass.RESTRICTED: (True, False),
    AccessClass.SHARED: (True, True),
}


# --- Results ---------------------------------------------------------------------------


@dataclass
class Cell:
    expect_allowed: bool
    allowed: bool
    status: str
    known_gap: str | None = None

    @property
    def mismatch(self) -> bool:
        return self.expect_allowed != self.allowed

    @property
    def failed(self) -> bool:
        return self.mismatch and not self.known_gap

    @property
    def known(self) -> bool:
        return self.mismatch and bool(self.known_gap)

    def render(self) -> str:
        return f"{'✗ ' if self.failed else '~ ' if self.known else '  '}{self.status}"


@dataclass
class Table:
    title: str
    rule: str
    columns: list[str]
    rows: dict[str, dict[str, Cell]] = field(default_factory=dict)

    def add(self, row: str, column: str, cell: Cell) -> None:
        cell.known_gap = KNOWN_GAPS.get((row, column)) or KNOWN_GAPS.get(row)
        self.rows.setdefault(row, {})[column] = cell

    def _lines(self, pick: Callable[[Cell], bool]) -> list[str]:
        return [
            f"{row} [{col}]: {c.status}, should be {'allowed' if c.expect_allowed else 'blocked'}"
            for row, cells in self.rows.items()
            for col, c in cells.items()
            if pick(c)
        ]

    def failures(self) -> list[str]:
        return self._lines(lambda c: c.failed)

    def known(self) -> list[tuple[str, str]]:
        return [
            (c.known_gap, f"{row} [{col}]: {c.status}")
            for row, cells in self.rows.items()
            for col, c in cells.items()
            if c.known
        ]

    def print(self) -> None:
        cells = [c for r in self.rows.values() for c in r.values()]
        failed, known = sum(c.failed for c in cells), sum(c.known for c in cells)
        counts = f"{len(cells) - failed - known} passed, {failed} failed"
        print(f"\n{self.title}  ({counts}{f', {known} known gap' if known else ''})")
        print(f"  Rule: {self.rule}")
        name_w = max(map(len, self.rows)) + 2
        col_w = max(16, *(len(c) + 2 for c in self.columns))
        print(f"  {'':<{name_w}}" + "".join(f"{c:<{col_w}}" for c in self.columns))
        for row, by_col in self.rows.items():
            line = "".join(
                f"{by_col[c].render() if c in by_col else '  -':<{col_w}}" for c in self.columns
            )
            print(f"  {row:<{name_w}}{line}")


def _try(
    fn: Callable[[], object], allowed_if: Callable[[object], bool] = bool
) -> tuple[bool, str]:
    """Run an SDK call; a refusal or an empty answer is ``blocked``, anything else ``allowed``."""
    try:
        value = fn()
    except AlbertHTTPError as err:
        return False, f"blocked ({err.response.status_code if err.response is not None else '?'})"
    if value is None or allowed_if(value):
        return True, "allowed"
    return False, "blocked (empty)"


def _cell(expect_allowed: bool, fn: Callable[[], object], **kwargs) -> Cell:
    return Cell(expect_allowed, *_try(fn, **kwargs))


def _readable(fn: Callable[[], object]) -> bool:
    return _try(fn, allowed_if=lambda _: True)[0]


def _wait_readable(fn: Callable[[], object], want: bool, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while _readable(fn) != want and time.monotonic() < deadline:
        time.sleep(3)


# --- Throwaway records -------------------------------------------------------------------


class Fixtures:
    """Throwaway records and grants, removed in reverse order at the end."""

    def __init__(self, admin: Albert):
        self.admin = admin
        self._cleanup: list[Callable[[], object]] = []
        location = admin.locations.get_or_create(
            location=Location(
                name=f"{PREFIX} lab", latitude=40.7, longitude=-74.0, address="1 ACL Test Way"
            )
        )
        self.storage = admin.storage_locations.get_or_create(
            storage_location=StorageLocation(
                name=f"{PREFIX} shelf", location=EntityLink(id=location.id), address="1 ACL"
            )
        )
        self.company = admin.companies.get_or_create(company=Company(name=f"{PREFIX} co"))

    def later(self, fn: Callable[[], object]) -> None:
        self._cleanup.append(fn)

    def close(self) -> None:
        for fn in reversed(self._cleanup):
            with suppress(AlbertHTTPError):
                fn()

    def inventory(self, cls: SecurityClass) -> InventoryItem:
        item = self.admin.inventory.create(
            inventory_item=InventoryItem(
                name=f"aclquick{uuid.uuid4().hex[:8]} {cls.value}",
                category=InventoryCategory.RAW_MATERIALS,
                unit_category=InventoryUnitCategory.MASS,
                security_class=cls,
                company=self.company,
            )
        )
        self.later(lambda: self.admin.inventory.delete(id=item.id))
        return item

    def lot(self, inventory_id: str, *, raw: bool = True) -> str:
        extra = {"cost": 1.0, "manufacturer_lot_number": f"{PREFIX}-lot"} if raw else {}
        lot = self.admin.lots.create(
            lots=[
                Lot(
                    inventory_id=inventory_id,
                    storage_location=EntityLink(id=self.storage.id),
                    initial_quantity=1.0,
                    inventory_on_hand=1.0,
                    **extra,
                )
            ]
        )[0]
        self.later(lambda: self.admin.lots.delete(id=lot.id))
        return lot.id

    def children(self, parent_id: str, *, inventory: bool = False) -> dict[str, str]:
        seeded = _seed_children(
            self.admin, parent_id, f"aclquick{uuid.uuid4().hex[:8]}", inventory=inventory
        )
        for key in (NOTE, ATTACHMENT_NOTE):
            self.later(lambda rid=seeded[key]: self.admin.notes.delete(id=rid))
        for key in (NOTE_ATTACHMENT, ATTACHMENT):
            self.later(lambda rid=seeded[key]: self.admin.attachments.delete(id=rid))
        return seeded

    def grant(self, resource_id: str, principal: str, level: str) -> None:
        grant(self.admin, resource_id, principal, level)
        self.later(lambda: revoke(self.admin, resource_id, principal))


# --- 1. Project class rules -------------------------------------------------------------


def project_class_rules(fx: Fixtures, user_a: Albert, user_a_id: str, user_b: Albert) -> Table:
    admin = fx.admin
    table = Table(
        "1. Project class rules: a project's formula and the formula's lot, note and file",
        "member (userA, ProjectEditor) reads and edits everything. Outsider (userB, no "
        "grant): shared = read + edit, restricted = read only, private and confidential = "
        "nothing.",
        [f"{c.value} {who}" for c in PROJECT_CLASSES for who in ("in", "out")],
    )
    targets = {}
    for cls in PROJECT_CLASSES:
        doc = ensure_static_doc(admin, cls)
        formula = ensure_static_formula(admin, doc)
        targets[cls] = (
            doc,
            formula,
            fx.lot(formula, raw=False),
            fx.children(formula, inventory=True),
        )
        fx.grant(doc.project_id, user_a_id, "ProjectEditor")
    for _doc, formula, *_ in targets.values():
        _wait_readable(lambda f=formula: user_a.inventory.get_by_id(id=f), True)

    def edit_formula(user: Albert, formula: str) -> object:
        item = admin.inventory.get_by_id(id=formula)
        item.description = f"{PREFIX} edit {uuid.uuid4().hex[:6]}"
        return user.inventory.update(inventory_item=item)

    def edit_lot(user: Albert, lot_id: str) -> object:
        lot = admin.lots.get_by_id(id=lot_id)
        lot.inventory_on_hand = float(lot.inventory_on_hand or 0) + 1
        return user.lots.update(lot=lot)

    def edit_note(user: Albert, note_id: str) -> object:
        note = admin.notes.get_by_id(id=note_id)
        note.note = f"{PREFIX} note {uuid.uuid4().hex[:6]}"
        return user.notes.update(note=note)

    def checks(user: Albert, pid: str, formula: str, lot: str, kids: dict, read: bool, edit: bool):
        note, note_file = kids[NOTE], kids[NOTE_ATTACHMENT]
        return {
            "Open the project": (read, lambda: user.projects.get_by_id(id=pid)),
            "Read formula": (read, lambda: user.inventory.get_by_id(id=formula)),
            "Read formula's lot": (read, lambda: user.lots.get_by_id(id=lot)),
            "Read formula's note": (read, lambda: user.notes.get_by_id(id=note)),
            "Read file on that note": (read, lambda: user.attachments.get_by_id(id=note_file)),
            "Edit formula": (edit, lambda: edit_formula(user, formula)),
            "Edit formula's lot": (edit, lambda: edit_lot(user, lot)),
            "Edit formula's note": (edit, lambda: edit_note(user, note)),
        }

    for cls, (doc, formula, lot, kids) in targets.items():
        out_read, out_edit = OUTSIDER_RULES[cls]
        for who, user, read, edit in (
            ("in", user_a, True, True),
            ("out", user_b, out_read, out_edit),
        ):
            for row, (expect, fn) in checks(
                user, doc.project_id, formula, lot, kids, read, edit
            ).items():
                table.add(row, f"{cls.value} {who}", _cell(expect, fn, allowed_if=lambda _: True))
    return table


# --- 2. Confidential raw material ---------------------------------------------------


def inventory_class(fx: Fixtures, user_b: Albert, user_b_id: str) -> tuple[Table, dict]:
    admin = fx.admin
    levels = ("InventoryViewer", "InventoryOwner")
    table = Table(
        "2. Confidential raw material: the item, its lot, note and file on that note",
        "hidden from anyone not named on the item; readable once named "
        "(InventoryViewer or InventoryOwner). A formula has no access of its own: it follows "
        "its project (section 1).",
        ["not named", *(f"named: {lv}" for lv in levels)],
    )
    raw = fx.inventory(SecurityClass.CONFIDENTIAL)
    subjects = {
        "Confidential raw material": (raw.id, fx.lot(raw.id), fx.children(raw.id, inventory=True)),
    }

    def reads(rid: str, lot: str, kids: dict) -> dict[str, Callable[[], object]]:
        return {
            "item": lambda: user_b.inventory.get_by_id(id=rid),
            "its lot": lambda: user_b.lots.get_by_id(id=lot),
            "its note": lambda: user_b.notes.get_by_id(id=kids[NOTE]),
            "file on its note": lambda: user_b.attachments.get_by_id(id=kids[NOTE_ATTACHMENT]),
        }

    def read_all(column: str, expect: bool) -> None:
        for label, (rid, lot, kids) in subjects.items():
            for what, fn in reads(rid, lot, kids).items():
                table.add(f"{label}: {what}", column, _cell(expect, fn, allowed_if=lambda _: True))

    read_all("not named", False)
    for level in levels:
        for rid, *_ in subjects.values():
            grant(admin, rid, user_b_id, level)
        try:
            for rid, *_ in subjects.values():
                _wait_readable(lambda r=rid: user_b.inventory.get_by_id(id=r), True)
            read_all(f"named: {level}", True)
        finally:
            for rid, *_ in subjects.values():
                revoke(admin, rid, user_b_id)
            for rid, *_ in subjects.values():
                _wait_readable(lambda r=rid: user_b.inventory.get_by_id(id=r), False)
    return table, {"raw": raw.id, "raw_lot": subjects["Confidential raw material"][1]}


# --- 3. Bypass routes --------------------------------------------------------------------


def _project_files(admin: Albert, pid: str) -> dict[str, str]:
    """A note, a file attached through a note and a direct file on the static project."""
    notes = admin.notes.get_by_parent_id(parent_id=pid)
    plain = next(n for n in notes if not n.attachments)
    wrapper = next(n for n in notes if n.attachments)
    direct = admin.attachments.get_by_parent_ids(parent_ids=[pid]).get(pid, [])
    return {NOTE: plain.id, NOTE_ATTACHMENT: wrapper.attachments[0].id, ATTACHMENT: direct[0].id}


def bypass_routes(fx: Fixtures, user_b: Albert, confidential_raw: dict[str, str]) -> Table:
    admin = fx.admin
    table = Table(
        "3. Bypass routes: other SDK calls an outsider (userB, no grant) might use",
        "every call is blocked; a refusal or an empty answer counts as blocked.",
        ["private project", "confidential project", "confidential raw"],
    )
    destination = ensure_static_doc(admin, AccessClass.SHARED).project_id

    def project_checks(doc: StaticDoc) -> dict[str, tuple]:
        pid = doc.project_id
        files = _project_files(admin, pid)
        fresh = fx.children(pid)
        formula = ensure_static_formula(admin, doc)
        notebook = admin.notebooks.list_by_parent_id(parent_id=pid)[0].id

        def edit_note() -> object:
            note = admin.notes.get_by_id(id=fresh[NOTE])
            note.note = f"{note.note} (edited by outsider)"
            return user_b.notes.update(note=note)

        def copy_notebook() -> object:
            copied = user_b.notebooks.copy(
                notebook_copy_info=NotebookCopyInfo(id=notebook, parent_id=destination),
                type=NotebookCopyType.PROJECT,
            )
            fx.later(lambda: admin.notebooks.delete(id=copied.id))
            return copied

        def worksheet() -> object:
            return WorksheetCollection(session=user_b.session).get_by_project_id(project_id=pid)

        return {
            "Read a project note by ID": (lambda: user_b.notes.get_by_id(id=files[NOTE]), None),
            "List the project's notes": (
                lambda: user_b.notes.get_by_parent_id(parent_id=pid),
                bool,
            ),
            "Download a project file by ID": (
                lambda: user_b.attachments.get_by_id(id=files[ATTACHMENT]),
                lambda a: bool(a.signed_url),
            ),
            "Download a note's file by ID": (
                lambda: user_b.attachments.get_by_id(id=files[NOTE_ATTACHMENT]),
                lambda a: bool(a.signed_url),
            ),
            "List the project's files": (
                lambda: user_b.attachments.get_by_parent_ids(parent_ids=[pid]),
                bool,
            ),
            "Edit a project note by ID": (edit_note, None),
            "Delete a project note by ID": (lambda: user_b.notes.delete(id=fresh[NOTE]), None),
            "Delete a project file by ID": (
                lambda: user_b.attachments.delete(id=fresh[ATTACHMENT]),
                None,
            ),
            "Bulk-get the project's formula": (
                lambda: user_b.inventory.get_by_ids(ids=[formula]),
                lambda items: any(i.id == formula for i in items),
            ),
            "Read the formula's ingredients": (
                lambda: user_b.product_design.get_unpacked_products(inventory_ids=[formula]),
                bool,
            ),
            "Read the project's worksheet": (worksheet, None),
            "Copy the project's notebook elsewhere": (copy_notebook, None),
        }

    for cls in (AccessClass.PRIVATE, AccessClass.CONFIDENTIAL):
        for row, (fn, allowed_if) in project_checks(ensure_static_doc(admin, cls)).items():
            kwargs = {"allowed_if": allowed_if or (lambda _: True)}
            table.add(row, f"{cls.value} project", _cell(False, fn, **kwargs))

    shared = fx.inventory(SecurityClass.SHARED)
    shared_lot = fx.lot(shared.id)
    raw, raw_lot = confidential_raw["raw"], confidential_raw["raw_lot"]
    raw_checks = {
        "Bulk-get it next to a shared item": (
            lambda: user_b.inventory.get_by_ids(ids=[shared.id, raw]),
            lambda items: any(i.id == raw for i in items),
        ),
        "Bulk-get its lot next to a shared lot": (
            lambda: user_b.lots.get_by_ids(ids=[shared_lot, raw_lot]),
            lambda lots: any(lot.id == raw_lot for lot in lots),
        ),
        "Delete its lot": (lambda: user_b.lots.delete(id=raw_lot), lambda _: True),
    }
    for row, (fn, allowed_if) in raw_checks.items():
        table.add(row, "confidential raw", _cell(False, fn, allowed_if=allowed_if))
    return table


# --- Main -------------------------------------------------------------------------------


def main() -> int:
    url = base_url()
    admin = load_identity("admin", url).client()
    a_identity, b_identity = load_identity("userA", url), load_identity("userB", url)
    user_a, user_b = a_identity.client(), b_identity.client()
    fx = Fixtures(admin)
    try:
        section1 = project_class_rules(fx, user_a, user_id(a_identity), user_b)
        section2, confidential_raw = inventory_class(fx, user_b, user_id(b_identity))
        section3 = bypass_routes(fx, user_b, confidential_raw)
    finally:
        fx.close()

    tables = (section1, section2, section3)
    for table in tables:
        table.print()

    failures = [(t.title.split(":")[0], f) for t in tables for f in t.failures()]
    known = [(t.title.split(":")[0], *k) for t in tables for k in t.known()]
    total = sum(len(r) for t in tables for r in t.rows.values())
    passed = total - len(failures) - len(known)
    print(f"\nSummary: {passed} passed, {len(failures)} failed, {len(known)} known gap(s)")
    print("  ✗ failed   ~ known gap (not counted)")
    for section, failure in failures:
        print(f"  [{section}] {failure}")
    for reason in dict.fromkeys(r for _, r, _ in known):
        print(f"\nKnown gap: {reason}")
        for section, r, line in known:
            if r == reason:
                print(f"  [{section}] {line}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
