from pydantic import Field, model_validator

from albert.core.shared.models.base import BaseSessionResource
from albert.resources.sheets import Sheet


class Worksheet(BaseSessionResource):
    """A worksheet entity.

    Attributes
    ----------
    sheets : List[Sheet]
        A list of sheet entities.
    project_name : str | None
        The name of the project.
    sheets_enabled : bool
        Whether the sheets are enabled.
    project_id : str
        The Albert ID of the project.
    """

    sheets: list[Sheet] = Field(alias="Sheets")
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
