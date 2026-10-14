"""Fast ACL smoke check: can a non-member reach hidden records through the SDK?

Runs in about a minute, without pytest and without changing anyone's role. userB holds
every policy but has no grant on the long-lived private/confidential projects
(``static_docs.py``), so every check below should be blocked. Each line is an SDK call made
as userB; anything that succeeds is a leak. Lot access must also mirror the parent
inventory item's access for the same user, with and without an inventory grant. Records
the checks write to or delete are created fresh each run and removed at the end.

The project-class matrix also uses userA (Full Access role, unchanged) as a project member
via a temporary ProjectEditor grant, to compare members and outsiders per project class.

    uv run python -m tests.acl.quick_check

Exits 1 when any leak is found.
"""

import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

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
from albert.resources.notes import Note
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

CLASSES = (AccessClass.PRIVATE, AccessClass.CONFIDENTIAL)
PREFIX = "SDK-ACL-quick"


@dataclass
class Result:
    leaked: bool
    detail: str


def _attempt(fn: Callable[[], object], leaked: Callable[[object], bool]) -> Result:
    """Run an SDK call as the non-member; a refusal is BLOCKED, a useful answer is a LEAK."""
    try:
        value = fn()
    except AlbertHTTPError as err:
        status = err.response.status_code if err.response is not None else "?"
        return Result(False, f"blocked ({status})")
    return Result(True, "LEAK") if leaked(value) else Result(False, "blocked (empty)")


def _always(_: object) -> bool:
    return True


class Fixtures:
    """Shared throwaway records and the cleanup that removes them."""

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


def _existing_children(admin: Albert, pid: str) -> dict[str, str]:
    """Ids of a note, a note-wrapped attachment and a direct attachment on the project."""
    notes = admin.notes.get_by_parent_id(parent_id=pid)
    plain = next(n for n in notes if not n.attachments)
    wrapper = next(n for n in notes if n.attachments)
    direct = admin.attachments.get_by_parent_ids(parent_ids=[pid]).get(pid, [])
    return {NOTE: plain.id, NOTE_ATTACHMENT: wrapper.attachments[0].id, ATTACHMENT: direct[0].id}


def _project_checks(
    fx: Fixtures, user: Albert, doc: StaticDoc, destination: str
) -> dict[str, Result]:
    admin, pid = fx.admin, doc.project_id
    ids = _existing_children(admin, pid)
    formula = ensure_static_formula(admin, doc)
    formula_lot = fx.lot(formula, raw=False)
    notebook = admin.notebooks.list_by_parent_id(parent_id=pid)[0].id
    fresh = fx.children(pid)

    def edit_note():
        note = admin.notes.get_by_id(id=fresh[NOTE])
        note.note = f"{note.note} (edited by non-member)"
        return user.notes.update(note=note)

    def copy_notebook():
        copied = user.notebooks.copy(
            notebook_copy_info=NotebookCopyInfo(id=notebook, parent_id=destination),
            type=NotebookCopyType.PROJECT,
        )
        fx.later(lambda: admin.notebooks.delete(id=copied.id))
        return copied

    return {
        "Open the project (baseline)": _attempt(lambda: user.projects.get_by_id(id=pid), _always),
        "Read a note by ID": _attempt(lambda: user.notes.get_by_id(id=ids[NOTE]), _always),
        "List the project's notes": _attempt(
            lambda: user.notes.get_by_parent_id(parent_id=pid), bool
        ),
        "Get a file by ID (download link)": _attempt(
            lambda: user.attachments.get_by_id(id=ids[ATTACHMENT]),
            lambda a: bool(a.signed_url),
        ),
        "Get a note's file by ID (download link)": _attempt(
            lambda: user.attachments.get_by_id(id=ids[NOTE_ATTACHMENT]),
            lambda a: bool(a.signed_url),
        ),
        "List the project's files": _attempt(
            lambda: user.attachments.get_by_parent_ids(parent_ids=[pid]), bool
        ),
        "Edit a note by ID": _attempt(edit_note, _always),
        "Delete a note by ID": _attempt(lambda: user.notes.delete(id=fresh[NOTE]), _always),
        "Delete a file by ID": _attempt(
            lambda: user.attachments.delete(id=fresh[ATTACHMENT]), _always
        ),
        "Read the project's formula by ID": _attempt(
            lambda: user.inventory.get_by_id(id=formula), _always
        ),
        "Bulk-get the project's formula": _attempt(
            lambda: user.inventory.get_by_ids(ids=[formula]),
            lambda items: any(i.id == formula for i in items),
        ),
        "Read the formula's ingredients": _attempt(
            lambda: user.product_design.get_unpacked_products(inventory_ids=[formula]), bool
        ),
        "Read the project's worksheet": _attempt(
            lambda: WorksheetCollection(session=user.session).get_by_project_id(project_id=pid),
            _always,
        ),
        "Read the formula's lot by ID": _attempt(
            lambda: user.lots.get_by_id(id=formula_lot), _always
        ),
        "Copy the project's notebook elsewhere": _attempt(copy_notebook, _always),
    }


def _readable(fn: Callable[[], object]) -> bool:
    try:
        fn()
    except AlbertHTTPError:
        return False
    return True


def _wait_readable(fn: Callable[[], object], want: bool, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while _readable(fn) != want and time.monotonic() < deadline:
        time.sleep(3)


def _inventory_checks(fx: Fixtures, user: Albert, user_id: str) -> dict[str, Result]:
    shared, hidden = fx.inventory(SecurityClass.SHARED), fx.inventory(SecurityClass.CONFIDENTIAL)
    shared_lot, hidden_lot = fx.lot(shared.id), fx.lot(hidden.id)
    checks = {
        "Open a confidential inventory item (baseline)": _attempt(
            lambda: user.inventory.get_by_id(id=hidden.id), _always
        ),
        "Bulk-get it next to a shared item": _attempt(
            lambda: user.inventory.get_by_ids(ids=[shared.id, hidden.id]),
            lambda items: any(i.id == hidden.id for i in items),
        ),
        "Read its lot by ID": _attempt(lambda: user.lots.get_by_id(id=hidden_lot), _always),
        "Bulk-get its lot next to a shared lot": _attempt(
            lambda: user.lots.get_by_ids(ids=[shared_lot, hidden_lot]),
            lambda lots: any(lot.id == hidden_lot for lot in lots),
        ),
        "Delete its lot": _attempt(lambda: user.lots.delete(id=hidden_lot), _always),
    }

    def mirror(item: InventoryItem, lot_id: str) -> Result:
        inv = _readable(lambda: user.inventory.get_by_id(id=item.id))
        lot = _readable(lambda: user.lots.get_by_id(id=lot_id))
        if inv == lot:
            return Result(False, f"match (both {'readable' if inv else 'blocked'})")
        side = "item readable, lot blocked" if inv else "lot readable, item blocked"
        return Result(True, f"MISMATCH: {side}")

    checks["Lot access mirrors item (shared, no grant)"] = mirror(shared, shared_lot)
    checks["Lot access mirrors item (confidential, no grant)"] = mirror(hidden, hidden_lot)
    for level in ("InventoryViewer", "InventoryOwner"):
        grant(fx.admin, hidden.id, user_id, level)
        try:
            _wait_readable(lambda: user.inventory.get_by_id(id=hidden.id), True)
            checks[f"Lot access mirrors item (confidential, {level})"] = mirror(hidden, hidden_lot)
        finally:
            revoke(fx.admin, hidden.id, user_id)
            _wait_readable(lambda: user.inventory.get_by_id(id=hidden.id), False)
    return checks


@dataclass
class ClassCheck:
    expect_readable: bool
    readable: bool
    status: str

    @property
    def wrong(self) -> bool:
        return self.expect_readable != self.readable


def _status(fn: Callable[[], object]) -> tuple[bool, str]:
    try:
        fn()
    except AlbertHTTPError as err:
        return False, f"blocked ({err.response.status_code if err.response is not None else '?'})"
    return True, "readable"


def _class_vs_project_checks(
    fx: Fixtures, user: Albert, shared: StaticDoc
) -> dict[str, ClassCheck]:
    """Does an inventory item's own class (FGC) win over the project it sits in?

    userB can open the shared project, so a formula there is readable unless its own
    inventory class hides it. A confidential raw material outside any project is the
    plain inventory case."""
    admin = fx.admin
    normal = ensure_static_formula(admin, shared)
    secret = ensure_static_formula(
        admin, shared, suffix="secret-formula", security_class=SecurityClass.CONFIDENTIAL
    )
    raw = fx.inventory(SecurityClass.CONFIDENTIAL)
    normal_lot, secret_lot = fx.lot(normal, raw=False), fx.lot(secret, raw=False)
    raw_lot = fx.lot(raw.id)
    cases = {
        "Open the shared project (baseline)": (
            True,
            lambda: user.projects.get_by_id(id=shared.project_id),
        ),
        "Normal formula in the shared project": (
            True,
            lambda: user.inventory.get_by_id(id=normal),
        ),
        "Secret (confidential) formula in the shared project": (
            False,
            lambda: user.inventory.get_by_id(id=secret),
        ),
        "Secret (confidential) raw material": (False, lambda: user.inventory.get_by_id(id=raw.id)),
        "Lot of the normal formula": (True, lambda: user.lots.get_by_id(id=normal_lot)),
        "Lot of the secret formula": (False, lambda: user.lots.get_by_id(id=secret_lot)),
        "Lot of the secret raw material": (False, lambda: user.lots.get_by_id(id=raw_lot)),
    }
    return {name: ClassCheck(expect, *_status(fn)) for name, (expect, fn) in cases.items()}


MATRIX_CLASSES = (
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


def _project_class_matrix(
    fx: Fixtures, user_a: Albert, user_a_id: str, user_b: Albert
) -> tuple[list[str], dict[str, dict[str, ClassCheck]]]:
    """A project's formula and the formula's lot and note, read and edited by a member
    (userA, ProjectEditor grant) and an outsider (userB, no grant) of each project class."""
    admin = fx.admin
    targets = {}
    for cls in MATRIX_CLASSES:
        doc = ensure_static_doc(admin, cls)
        formula = ensure_static_formula(admin, doc)
        lot = fx.lot(formula, raw=False)
        note = admin.notes.create(note=Note(parent_id=formula, note=f"{PREFIX} formula note"))
        fx.later(lambda nid=note.id: admin.notes.delete(id=nid))
        targets[cls] = (doc, formula, lot, note.id)

    for doc, *_ in targets.values():
        grant(admin, doc.project_id, user_a_id, "ProjectEditor")
        fx.later(lambda pid=doc.project_id: revoke(admin, pid, user_a_id))
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
        note.note = f"{PREFIX} formula note {uuid.uuid4().hex[:6]}"
        return user.notes.update(note=note)

    columns = [f"{c.value} {who}" for c in MATRIX_CLASSES for who in ("in", "out")]
    rows: dict[str, dict[str, ClassCheck]] = {}
    for cls, (_doc, formula, lot, note) in targets.items():
        out_read, out_edit = OUTSIDER_RULES[cls]
        for who, user, can_read, can_edit in (
            ("in", user_a, True, True),
            ("out", user_b, out_read, out_edit),
        ):
            col = f"{cls.value} {who}"
            actions = {
                "Read formula": (can_read, lambda u=user, f=formula: u.inventory.get_by_id(id=f)),
                "Read formula's lot": (can_read, lambda u=user, x=lot: u.lots.get_by_id(id=x)),
                "Read formula's note": (can_read, lambda u=user, x=note: u.notes.get_by_id(id=x)),
                "Edit formula": (can_edit, lambda u=user, f=formula: edit_formula(u, f)),
                "Edit formula's lot": (can_edit, lambda u=user, x=lot: edit_lot(u, x)),
                "Edit formula's note": (can_edit, lambda u=user, x=note: edit_note(u, x)),
            }
            for name, (expect, fn) in actions.items():
                ok, status = _status(fn)
                rows.setdefault(name, {})[col] = ClassCheck(expect, ok, "ok" if ok else status)
    return columns, rows


def _confidential_inheritance(
    fx: Fixtures, user_a: Albert, user_a_id: str, user_b: Albert
) -> tuple[list[str], dict[str, dict[str, ClassCheck]]]:
    """A confidential inventory item, and a formula in a private or confidential project: the
    record, its lot, its note and the file on that note are readable only by admin and by
    someone named on it (userA: InventoryViewer on the item, ProjectViewer on the project).
    A standard user who is not named (userB, every policy) is blocked from all of them."""
    admin = fx.admin
    raw = fx.inventory(SecurityClass.CONFIDENTIAL)
    subjects = {"Confidential raw material": (raw.id, raw.id, "InventoryViewer")}
    for cls in (AccessClass.PRIVATE, AccessClass.CONFIDENTIAL):
        doc = ensure_static_doc(admin, cls)
        subjects[f"Formula in a {cls.value} project"] = (
            ensure_static_formula(admin, doc),
            doc.project_id,
            "ProjectViewer",
        )
    seeded = {
        label: (rid, fx.lot(rid, raw=rid == raw.id), fx.children(rid, inventory=True))
        for label, (rid, _, _) in subjects.items()
    }
    for _label, (rid, grant_on, level) in subjects.items():
        grant(admin, grant_on, user_a_id, level)
        fx.later(lambda g=grant_on: revoke(admin, g, user_a_id))
        _wait_readable(lambda r=rid: user_a.inventory.get_by_id(id=r), True)

    users = {"admin": (admin, True), "named": (user_a, True), "not named": (user_b, False)}
    columns = [f"{who}" for who in users]
    rows: dict[str, dict[str, ClassCheck]] = {}
    for label, (rid, lot, kids) in seeded.items():
        reads = {
            "item": lambda u, r=rid: u.inventory.get_by_id(id=r),
            "its lot": lambda u, x=lot: u.lots.get_by_id(id=x),
            "its note": lambda u, x=kids[NOTE]: u.notes.get_by_id(id=x),
            "file on its note": lambda u, x=kids[NOTE_ATTACHMENT]: u.attachments.get_by_id(id=x),
        }
        for what, fn in reads.items():
            name = f"{label}: {what}"
            for who, (client, expect) in users.items():
                ok, status = _status(lambda c=client, f=fn: f(c))
                rows.setdefault(name, {})[who] = ClassCheck(expect, ok, "ok" if ok else status)
    return columns, rows


def main() -> int:
    url = base_url()
    admin = load_identity("admin", url).client()
    user_b = load_identity("userB", url)
    user = user_b.client()
    user_a = load_identity("userA", url)
    fx = Fixtures(admin)
    try:
        destination = ensure_static_doc(admin, AccessClass.SHARED).project_id
        rows: dict[str, dict[AccessClass, Result]] = {}
        for cls in CLASSES:
            checks = _project_checks(fx, user, ensure_static_doc(admin, cls), destination)
            for name, result in checks.items():
                rows.setdefault(name, {})[cls] = result
        inventory = _inventory_checks(fx, user, user_id(user_b))
        by_class = _class_vs_project_checks(fx, user, ensure_static_doc(admin, AccessClass.SHARED))
        columns, matrix = _project_class_matrix(fx, user_a.client(), user_id(user_a), user)
        inherit_cols, inherit = _confidential_inheritance(
            fx, user_a.client(), user_id(user_a), user
        )
    finally:
        fx.close()

    width = max(map(len, [*rows, *inventory, *by_class])) + 2
    print(f"\n{'Non-member (userB) tries to':<{width}}{'private':<18}confidential")
    for name, by_cls in rows.items():
        print(f"{name:<{width}}" + "".join(f"{by_cls[c].detail:<18}" for c in CLASSES))
    print()
    for name, result in inventory.items():
        print(f"{name:<{width}}{result.detail}")

    print(f"\n{'Inventory class vs project access (userB)':<{width}}{'expected':<18}got")
    for name, chk in by_class.items():
        expected = "readable" if chk.expect_readable else "blocked"
        flag = "" if not chk.wrong else "   <-- WRONG"
        print(f"{name:<{width}}{expected:<18}{chk.status}{flag}")

    print("\nProject class x membership (in = userA, ProjectEditor; out = userB, no grant)")
    print(f"{'':<22}" + "".join(f"{c:<18}" for c in columns))
    for name, cells in matrix.items():
        line = "".join(
            f"{cells[c].status + (' !' if cells[c].wrong else ''):<18}" for c in columns
        )
        print(f"{name:<22}{line}")

    iw = max(map(len, inherit)) + 2
    print("\nConfidential inheritance (named = userA with a grant; not named = userB)")
    print(f"{'':<{iw}}" + "".join(f"{c:<18}" for c in inherit_cols))
    for name, cells in inherit.items():
        line = "".join(
            f"{cells[c].status + (' !' if cells[c].wrong else ''):<18}" for c in inherit_cols
        )
        print(f"{name:<{iw}}{line}")

    leaks = [f"{n} ({c.value})" for n, by in rows.items() for c, r in by.items() if r.leaked]
    leaks += [
        f"{n}: {r.detail}" if r.detail.startswith("MISMATCH") else f"{n} (confidential inventory)"
        for n, r in inventory.items()
        if r.leaked
    ]
    leaks += [
        f"{n}: expected {'readable' if c.expect_readable else 'blocked'}, got {c.status}"
        for n, c in by_class.items()
        if c.wrong
    ]
    leaks += [
        f"{name} [{col}]: {'allowed' if c.readable else 'blocked'}, should be "
        f"{'allowed' if c.expect_readable else 'blocked'}"
        for name, cells in matrix.items()
        for col, c in cells.items()
        if c.wrong
    ]
    leaks += [
        f"{name} [{col}]: {'readable' if c.readable else 'blocked'}, should be "
        f"{'readable' if c.expect_readable else 'blocked'}"
        for name, cells in inherit.items()
        for col, c in cells.items()
        if c.wrong
    ]
    print(f"\n{len(leaks)} leak(s)" + (":" if leaks else ""))
    for leak in leaks:
        print(f"  - {leak}")
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
