"""Long-lived projects whose documents stay in the document-search index across runs.

Document search indexes asynchronously and slowly, so a per-run seed is never searchable
in time. One project per class is created once, found again by its fixed canary on later
runs, and never torn down. Each project holds canary-named files (found by title) and a
text file whose body carries a separate token that no file name contains (found by
content). Missing documents are seeded on first use and backfilled on later runs.
"""

import io
from dataclasses import dataclass

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.inventory import InventoryCategory
from albert.resources.locations import Location
from albert.resources.notebooks import Notebook
from albert.resources.projects import Project, ProjectClass
from albert.resources.sheets import Component
from tests.acl.contract.fgc import AccessClass
from tests.acl.http import call
from tests.acl.identities import AclSetupError
from tests.acl.world import _must, _seed_children, _seed_notebook_image

STATIC_PREFIX = "SDK-ACL-static-docsearch"


@dataclass(frozen=True)
class StaticDoc:
    access_class: AccessClass
    project_id: str
    canary: str
    content_token: str
    content_file: str


def _find(admin: Albert, canary: str) -> str | None:
    resp = call(admin, "GET", "/api/v3/projects/search", params={"text": canary})
    for item in resp.items():
        if str(item.get("description", "")).startswith(canary):
            # Project search returns ids without the ``PRO`` prefix (``MO123`` for ``PROMO123``).
            rid = item["albertId"]
            return rid if rid.startswith("PRO") else f"PRO{rid}"
    return None


def _create(admin: Albert, cls: AccessClass, canary: str) -> str:
    location = _must(
        "static location",
        lambda: admin.locations.get_or_create(
            location=Location(
                name=f"{STATIC_PREFIX} lab",
                latitude=40.7,
                longitude=-74.0,
                address="1 ACL Test Way",
            )
        ),
    )
    project = _must(
        f"static {cls.value} project",
        lambda: admin.projects.create(
            project=Project(
                description=f"{canary} {STATIC_PREFIX} {cls.value}",
                locations=[EntityLink(id=location.id)],
                project_class=ProjectClass(cls.value),
            )
        ),
    )
    _seed_children(admin, project.id, canary)
    notebook = _must(
        "static notebook",
        lambda: admin.notebooks.create(
            notebook=Notebook(name=f"{canary} {STATIC_PREFIX} nb", parent_id=project.id)
        ),
    )
    _seed_notebook_image(admin, notebook, canary)
    return project.id


def _ensure_content_doc(admin: Albert, doc: StaticDoc) -> None:
    marker = f"ACL content document {doc.content_file}"
    notes = call(admin, "GET", "/api/v3/notes", params={"parentId": doc.project_id}).items()
    if any(n.get("note") == marker for n in notes):
        return
    _must(
        "static content document",
        lambda: admin.attachments.upload_and_attach_file_as_note(
            parent_id=doc.project_id,
            file_data=io.BytesIO(f"ACL document body {doc.content_token}\n".encode()),
            note_text=marker,
            file_name=doc.content_file,
            content_type="text/plain",
        ),
    )


def ensure_static_doc(admin: Albert, cls: AccessClass) -> StaticDoc:
    """Return the class's static document project, creating or backfilling it as needed."""
    canary = f"aclstaticdoc{cls.value}"
    pid = _find(admin, canary) or _create(admin, cls, canary)
    doc = StaticDoc(
        access_class=cls,
        project_id=pid,
        canary=canary,
        content_token=f"aclbodytoken{cls.value}",
        content_file=f"{canary}-notes.txt",
    )
    _ensure_content_doc(admin, doc)
    return doc


def ensure_static_formula(admin: Albert, doc: StaticDoc) -> str:
    """Return the inventory id of the project's long-lived formula, creating it once."""
    name = f"{doc.canary}-formula"
    sheets = WorksheetCollection(session=admin.session)
    try:
        worksheet = sheets.get_by_project_id(project_id=doc.project_id)
    except AlbertHTTPError:
        worksheet = _must(
            "static worksheet", lambda: sheets.setup_worksheet(project_id=doc.project_id)
        )
    for sheet in worksheet.sheets:
        for column in sheet.columns:
            if column.name == name and column.inventory_id:
                return column.inventory_id
    if not worksheet.sheets:
        worksheet = _must(
            "static sheet",
            lambda: sheets.add_sheet(project_id=doc.project_id, sheet_name="acl"),
        )
    hit = next(iter(admin.inventory.search(category=InventoryCategory.RAW_MATERIALS, max_items=1)))
    raw = admin.inventory.get_by_id(id=hit.id)
    column = _must(
        "static formula",
        lambda: worksheet.sheets[0].add_formulation(
            formulation_name=name, components=[Component(inventory_item=raw, amount=100)]
        ),
    )
    if not column.inventory_id:
        raise AclSetupError("add_formulation returned no formula inventory id")
    return column.inventory_id
