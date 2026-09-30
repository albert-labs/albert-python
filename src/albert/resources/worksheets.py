from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.base import BaseSessionResource
from albert.resources.sheets import Sheet


class Worksheet(BaseSessionResource):
    """An Excel-like grid paired one-to-one with a Project.

    A Worksheet is the command center where formulations are designed. It groups
    one or more Sheets ([`Sheet`][albert.resources.sheets.Sheet]), each an
    interactive grid organized into stacked sections (Product Design, Process
    Design, Results, and Apps). Building a formulation on a Sheet is what
    registers a Formula inventory item.

    Retrieve a Worksheet with
    [`get_by_project_id`][albert.collections.worksheets.WorksheetCollection.get_by_project_id],
    then work with its Sheets through the [`sheets`][albert.resources.worksheets.Worksheet.sheets] attribute. Editing the
    contents of a Sheet is done through the [`Sheet`][albert.resources.sheets.Sheet]
    objects themselves, which remain connected to the live session.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        worksheet = client.worksheets.get_by_project_id(project_id="PROA9999999")
        for sheet in worksheet.sheets:
            print(sheet.id, sheet.name)
        ```"""

    sheets: list[Sheet] = Field(default_factory=list, alias="Sheets")
    """The Sheets contained in this Worksheet."""

    project_name: str | None = Field(default=None, alias="projectName")
    """The name of the paired Project."""

    sheets_enabled: bool = Field(default=True, alias="sheetEnabled")
    """Whether Sheets are enabled for this Worksheet."""

    project_id: str = Field(alias="projectId")
    """The ID of the paired Project (format ``PRO...``)."""

    @model_validator(mode="after")
    def add_session_to_sheets(self):
        if self.session is not None:
            for s in self.sheets:
                s._session = self.session
                for d in s.designs:
                    d._session = self.session
        return self


class WorksheetSearchInventoryLine(BaseAlbertModel):
    """An ingredient row on a formula search hit."""

    id: InventoryId | None = None
    """The inventory ID of the ingredient (format ``INV...``)."""

    name: str | None = None
    """The name of the ingredient."""


class WorksheetSearchTag(BaseAlbertModel):
    """A tag on a formula search hit."""

    tag_id: str | None = Field(default=None, alias="tagId")
    """The ID of the tag (format ``TAG...``)."""

    tag_name: str | None = Field(default=None, alias="tagName")
    """The name of the tag."""


class WorksheetSearchItem(BaseAlbertModel):
    """A lightweight formula result returned by worksheet search.

    Returned by
    [`search`][albert.collections.worksheets.WorksheetCollection.search],
    this is a partially populated view of a Formula inventory item built on a
    Sheet, optimized for fast lookups. Pass its ``id`` to
    [`get_by_id`][albert.collections.inventory.InventoryCollection.get_by_id]
    to obtain the fully populated
    [`InventoryItem`][albert.resources.inventory.InventoryItem]."""

    id: InventoryId | None = Field(default=None, alias="albertId")
    """The Formula inventory ID (format ``INV...``)."""

    name: str | None = None
    """The display name of the formula."""

    inventory: list[WorksheetSearchInventoryLine] | None = None
    """The ingredient rows on the formula."""

    tags: list[WorksheetSearchTag] | None = None
    """The tags on the formula."""
