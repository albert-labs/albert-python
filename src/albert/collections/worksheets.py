from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ProjectId
from albert.resources.worksheets import Worksheet


class WorksheetCollection(BaseCollection):
    """WorksheetCollection is a collection class for managing Worksheet entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{WorksheetCollection._api_version}/worksheet"

    def _add_session_to_sheets(self, response_json: dict):
        sheets = response_json.get("Sheets")
        if sheets:
            for s in sheets:
                s["session"] = self.session
                s["project_id"] = response_json["projectId"]
        response_json["session"] = self.session
        return response_json

    def get_by_project_id(self, *, project_id: ProjectId) -> Worksheet:
        """Retrieve a worksheet by its project ID. Projects and Worksheets are 1:1 in the Albert platform.

        Parameters
        ----------
        project_id : str
            The project ID to retrieve the worksheet for.

        Returns
        -------
        Worksheet
            The Worksheet object for that project.
        """

        params = {"type": "project", "id": project_id}
        response = self.session.get(self.base_path, params=params)

        response_json = response.json()

        # Sheets are themselves collections, and therefore need access to the session
        response_json = self._add_session_to_sheets(response_json)

        return Worksheet(**response_json)

    def setup_worksheet(self, *, project_id: ProjectId, add_sheet=False) -> Worksheet:
        """Setup a new worksheet for a project.

        Parameters
        ----------
        project_id : str
            The project ID to setup the worksheet for.
        add_sheet : bool, optional
            Whether to add a blank sheet to the worksheet, by default False

        Returns
        -------
        Worksheet
            The Worksheet object for the project.
        """

        params = {"sheets": str(add_sheet).lower()}
        path = f"{self.base_path}/{project_id}/setup"
        self.session.post(path, json=params)
        return self.get_by_project_id(project_id=project_id)

    def setup_new_sheet_from_template(
        self, *, project_id: ProjectId, sheet_template_id: str, sheet_name: str
    ) -> Worksheet:
        """Create a new sheet in the Worksheet related to the specified Project from a template.

        Parameters
        ----------
        project_id : str
            _description_
        sheet_template_id : str
            _description_
        sheet_name : str
            _description_

        Returns
        -------
        Worksheet
            The Worksheet object for the project.
        """
        payload = {"name": sheet_name}
        params = {"templateId": sheet_template_id}
        path = f"{self.base_path}/project/{project_id}/sheets"
        self.session.post(path, json=payload, params=params)
        return self.get_by_project_id(project_id=project_id)

    def add_sheet(self, *, project_id: ProjectId, sheet_name: str) -> Worksheet:
        """Create a new blank sheet in the Worksheet with the specified name.

        Parameters
        ----------
        project_id : str
            The project ID for the Worksheet to add the sheet to.
        sheet_name : str
            The name of the new sheet.

        Returns
        -------
        Worksheet
            The Worksheet object for the project.
        """
        payload = {"name": sheet_name}
        url = f"{self.base_path}/project/{project_id}/sheets"
        self.session.put(url=url, json=payload)
        return self.get_by_project_id(project_id=project_id)
