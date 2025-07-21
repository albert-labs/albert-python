from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ProjectId
from albert.resources.sheets import CellType, Sheet
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

    @validate_call
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

    @validate_call
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

    @validate_call
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

    @validate_call
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

    @validate_call
    def duplicate_sheet(
        self,
        *,
        project_id: ProjectId,
        source_sheet_name: str,
        new_sheet_name: str,
        copy_all_pd_rows: bool = True,
        copy_all_pinned_columns: bool = True,
        copy_all_unpinned_columns: bool = True,
        column_names: list[str] | None = None,
        task_row_names: list[str] | None = None,
    ) -> Worksheet:
        """Duplicate an existing sheet within the same project.

        This creates a new sheet based on the specified source sheet. You can control
        which Product Design (PD) & Results rows and columns are copied using the available options.
        The final list of columns copied is the union of:
            - all pinned columns (if copy_all_pinned_columns is True)
            - all unpinned columns (if copy_all_unpinned_columns is True)
            - explicitly listed column names (column_names)

        Parameters
        ----------
        project_id : str
            The project ID under which the sheet exists.
        source_sheet_name : str
            The name of the existing sheet to duplicate.
        new_sheet_name : str
            The name of the new sheet to create.
        copy_all_pd_rows : bool, optional
            When True, all PD (Product Design) rows from the source sheet are copied.
            When False, only rows corresponding to the selected columns will be copied.
            Default is True.
        copy_all_pinned_columns : bool, optional
            If True, includes all pinned columns from the source sheet. Default is True.
        copy_all_unpinned_columns : bool, optional
            If True, includes all unpinned columns from the source sheet. Default is True.
        column_names : list of str, optional
            A list of column names to explicitly copy. These are resolved internally
            to column IDs using the sheet's product design grid.
        task_row_names : list of str, optional
            List of task row names to include from the tasks.

        Returns
        -------
        Worksheet
            The Worksheet entity containing newly created sheet.
        """

        def _get_sheet_from_worksheet(sheet_name: str, worksheet: Worksheet) -> Sheet:
            """Get the sheet from the worksheet by sheet name."""
            sheet = next((s for s in worksheet.sheets if s.name == sheet_name), None)
            if not sheet:
                raise ValueError(f"Sheet with name {sheet_name} not found in the Worksheet.")
            return sheet

        def _get_columns_to_copy(sheet: Sheet, input_column_names: list[str] | None) -> list[str]:
            """Determine which columns to copy based on the provided options."""
            sheet_columns = sheet.columns
            # Map column names to IDs
            all_columns = {col.name: col.column_id for col in sheet_columns}

            # If both flags are true, copy everything
            if copy_all_pinned_columns and copy_all_unpinned_columns:
                return set(all_columns.values())

            columns_to_copy: set[str] = set()
            # Copy pinned columns
            if copy_all_pinned_columns:
                columns_to_copy.update(
                    col.column_id for col in sheet_columns if getattr(col, "pinned", False)
                )

            # Copy unpinned columns
            if copy_all_unpinned_columns:
                columns_to_copy.update(
                    col.column_id for col in sheet_columns if not getattr(col, "pinned", False)
                )

            # Add any explicitly specified columns
            if input_column_names:
                for name in input_column_names:
                    if name not in all_columns:
                        raise ValueError(f"Column name {name!r} not found in sheet {sheet.name!r}")
                    columns_to_copy.add(all_columns[name])

            return columns_to_copy

        def _get_task_rows_to_copy(sheet: Sheet, input_row_names: list[str] | None) -> list[str]:
            """Determine which task rows to copy"""
            task_rows = []

            sheet_rows = sheet.rows
            if not input_row_names:
                # Copy all task rows if no input rows specified
                for row in sheet_rows:
                    if row.type == CellType.TAS:
                        task_rows.append(row.row_id)
                return task_rows

            name_to_id = {row.name: row.row_id for row in sheet_rows}
            for name in input_row_names:
                row_id = name_to_id.get(name)
                if row_id:
                    task_rows.append(row_id)
                else:
                    raise ValueError(f"Task row name '{name}' not found in the grid.")
            return task_rows

        worksheet = self.get_by_project_id(project_id=project_id)
        sheet = _get_sheet_from_worksheet(sheet_name=source_sheet_name, worksheet=worksheet)
        columns = _get_columns_to_copy(sheet=sheet, input_column_names=column_names)
        task_rows = _get_task_rows_to_copy(sheet=sheet, input_row_names=task_row_names)

        payload = {
            "name": new_sheet_name,
            "sourceData": {
                "projectId": project_id,
                "sheetId": sheet.id,
                "Columns": [{"id": col_id} for col_id in columns],
                "copyAllPDRows": copy_all_pd_rows,
                "TaskRows": [{"id": row_id} for row_id in task_rows],
            },
        }

        path = f"{self.base_path}/project/{project_id}/sheets"
        self.session.put(path, json=payload)
        return self.get_by_project_id(project_id=project_id)
