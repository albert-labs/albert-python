"""Fast ACL smoke check: can a non-member reach hidden records through the SDK?

Runs in about a minute, without pytest and without changing anyone's role. userB holds
every policy but has no grant on the long-lived private/confidential projects
(``static_docs.py``), so every check below should be blocked. Each line is an SDK call made
as userB; anything that succeeds is a leak. Lot access must also mirror the parent
inventory item's access for the same user, with and without an inventory grant. Records
the checks write to or delete are created fresh each run and removed at the end.

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

    def children(self, parent_id: str) -> dict[str, str]:
        seeded = _seed_children(self.admin, parent_id, f"aclquick{uuid.uuid4().hex[:8]}")
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


def main() -> int:
    url = base_url()
    admin = load_identity("admin", url).client()
    user_b = load_identity("userB", url)
    user = user_b.client()
    fx = Fixtures(admin)
    try:
        destination = ensure_static_doc(admin, AccessClass.SHARED).project_id
        rows: dict[str, dict[AccessClass, Result]] = {}
        for cls in CLASSES:
            checks = _project_checks(fx, user, ensure_static_doc(admin, cls), destination)
            for name, result in checks.items():
                rows.setdefault(name, {})[cls] = result
        inventory = _inventory_checks(fx, user, user_id(user_b))
    finally:
        fx.close()

    width = max(map(len, [*rows, *inventory])) + 2
    print(f"\n{'Non-member (userB) tries to':<{width}}{'private':<18}confidential")
    for name, by_cls in rows.items():
        print(f"{name:<{width}}" + "".join(f"{by_cls[c].detail:<18}" for c in CLASSES))
    print()
    for name, result in inventory.items():
        print(f"{name:<{width}}{result.detail}")

    leaks = [f"{n} ({c.value})" for n, by in rows.items() for c, r in by.items() if r.leaked]
    leaks += [
        f"{n}: {r.detail}" if r.detail.startswith("MISMATCH") else f"{n} (confidential inventory)"
        for n, r in inventory.items()
        if r.leaked
    ]
    print(f"\n{len(leaks)} leak(s)" + (":" if leaks else ""))
    for leak in leaks:
        print(f"  - {leak}")
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
