from pydantic import Field, model_validator

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

    Attributes
    ----------
    sheets : list[Sheet]
        The Sheets contained in this Worksheet.
    project_name : str | None
        The name of the paired Project.
    sheets_enabled : bool
        Whether Sheets are enabled for this Worksheet.
    project_id : str
        The ID of the paired Project (format ``PRO...``).

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        worksheet = client.worksheets.get_by_project_id(project_id="PRO1")
        for sheet in worksheet.sheets:
            print(sheet.id, sheet.name)
        ```
    """

    sheets: list[Sheet] = Field(default_factory=list, alias="Sheets")
    project_name: str | None = Field(default=None, alias="projectName")
    sheets_enabled: bool = Field(default=True, alias="sheetEnabled")
    project_id: str = Field(alias="projectId")

    @model_validator(mode="after")
    def add_session_to_sheets(self):
        if self.session is not None:
            for s in self.sheets:
                s._session = self.session
                for d in s.designs:
                    d._session = self.session
        return self
