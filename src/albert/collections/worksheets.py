from albert.collections.base import BaseCollection
from albert.resources.worksheets import Worksheet
from albert.session import AlbertSession


class WorksheetCollection(BaseCollection):
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

    def get_by_project_id(self, *, project_id: str) -> Worksheet:
        if not project_id.startswith("PRO"):
            project_id = "PRO" + project_id
        params = {"type": "project", "id": project_id}
        response = self.session.get(self.base_path, params=params)

        response_json = response.json()

        # Sheets are themselves collections, and therefore need access to the session
        response_json = self._add_session_to_sheets(response_json)

        return Worksheet(**response_json)

    def setup_worksheet(self, *, project_id: str, add_sheet=False) -> Worksheet:
        if not project_id.startswith("PRO"):
            project_id = f"PRO{project_id}"
        params = {"sheets": str(add_sheet).lower()}
        path = f"{self.base_path}/{project_id}/setup"
        self.session.post(path, json=params)
        return self.get_by_project_id(project_id=project_id)

    def setup_new_worksheet_blank(
        self, *, project_id: str, sheet_name: str | None = None
    ) -> Worksheet:
        payload = {"name": sheet_name}
        payload = {k: v for k, v in payload.items() if v is not None}
        if not project_id.startswith("PRO"):
            project_id = "PRO" + project_id
        path = f"{self.base_path}/project/{project_id}/sheets"
        self.session.post(path, json=payload)
        return self.get_by_project_id(project_id=project_id)

    def setup_new_worksheet_from_template(
        self, *, project_id: str, sheet_template_id: str, sheet_name: str
    ):
        payload = {"name": sheet_name}
        params = {"templateId": sheet_template_id}
        if not project_id.startswith("PRO"):
            project_id = "PRO" + project_id
        path = f"{self.base_path}/project/{project_id}/sheets"
        self.session.post(path, json=payload, params=params)
        return self.get_by_project_id(project_id=project_id)

    def add_sheet(self, *, project_id: str, sheet_name: str) -> Worksheet:
        payload = {"name": sheet_name}
        project_id = "PRO" + project_id if not project_id.startswith("PRO") else project_id
        url = f"{self.base_path}/project/{project_id}/sheets"
        self.session.put(url=url, json=payload)
        return self.get_by_project_id(project_id=project_id)
