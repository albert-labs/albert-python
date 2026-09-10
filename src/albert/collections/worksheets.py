from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.custom_templates import CustomTemplatesCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ProjectId, SearchProjectId
from albert.core.utils import ensure_list
from albert.resources.acls import ACLContainer
from albert.resources.custom_templates import CustomTemplate
from albert.resources.worksheets import Worksheet, WorksheetSearchItem
from albert.utils.worksheets import (
    get_columns_to_copy,
    get_prg_rows_to_copy,
    get_sheet_from_worksheet,
    get_task_rows_to_copy,
)


class WorksheetCollection(BaseCollection):
    """Manage Worksheets in the Albert platform.

    A Worksheet is the Excel-like command center where formulations are designed.
    Each Worksheet is paired one-to-one with a Project ([`Project`][albert.resources.projects.Project])
    and is retrieved by that Project's ID with [`get_by_project_id`][albert.collections.worksheets.WorksheetCollection.get_by_project_id].

    A Worksheet holds one or more Sheets ([`Sheet`][albert.resources.sheets.Sheet]).
    Each Sheet is an interactive grid organized into stacked sections (given by
    [`DesignType`][albert.resources.sheets.DesignType]): Product Design (where
    formulations are built), Process Design, Results (Property Tasks and their
    data), and Apps (insights and notes). Building a formulation on a Sheet is
    what registers a Formula inventory item
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]): Formulas originate
    here rather than through the Inventory collection.

    This collection manages Worksheet- and Sheet-level structure (retrieving a
    Worksheet, adding Sheets, duplicating Sheets, and creating Sheet templates).
    Editing the contents of a Sheet (columns, rows, cells, and formulations) is
    done through the returned [`Sheet`][albert.resources.sheets.Sheet] objects.

    This collection is accessed as ``client.worksheets``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        worksheet = client.worksheets.get_by_project_id(project_id="PROA9999999")
        for sheet in worksheet.sheets:
            print(sheet.id, sheet.name)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for worksheet requests.

    Methods
    -------
    get_by_project_id(project_id) -> Worksheet
        Get the Worksheet paired with a Project.
    search(...) -> Iterator[WorksheetSearchItem]
        Search for formulas across Worksheets matching the given filters.
    setup_worksheet(project_id, add_sheet=False) -> Worksheet
        Initialize a Worksheet for a Project that does not yet have one.
    add_sheet(project_id, sheet_name) -> Worksheet
        Add a new blank Sheet to a Worksheet.
    setup_new_sheet_from_template(project_id, sheet_template_id, sheet_name) -> Worksheet
        Add a new Sheet built from an existing Sheet template.
    duplicate_sheet(project_id, source_sheet_name, new_sheet_name, ...) -> Worksheet
        Copy an existing Sheet into a new Sheet within the same Project.
    create_sheet_template(project_id, source_sheet_name, template_name, ...) -> CustomTemplate
        Save an existing Sheet as a reusable Sheet template.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a WorksheetCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
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
        """Get the Worksheet paired with a Project.

        Projects and Worksheets are one-to-one in Albert, so a Project ID uniquely
        identifies a Worksheet. This is the usual entry point for working with a
        Worksheet: the returned object exposes its Sheets
        ([`Sheet`][albert.resources.sheets.Sheet]), each of which can then be
        edited in place.

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            worksheet = client.worksheets.get_by_project_id(project_id="PROA9999999")
            sheet = worksheet.sheets[0]
            print(sheet.name)
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project whose Worksheet to retrieve (format ``PRO...``).

        Returns
        -------
        Worksheet
            The Worksheet paired with the Project.
        """

        params = {"type": "project", "id": project_id}
        response = self.session.get(self.base_path, params=params)

        response_json = response.json()

        # Sheets are themselves collections, and therefore need access to the session
        response_json = self._add_session_to_sheets(response_json)
        return Worksheet(**response_json)

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        project_id: SearchProjectId | None = None,
        sheet_id: str | None = None,
        tags: str | list[str] | None = None,
        albert_id: str | list[str] | None = None,
        state: str | list[str] | None = None,
        predecessor: str | list[str] | None = None,
        data_template: str | list[str] | None = None,
        inventory_name: str | list[str] | None = None,
        inventory_id: str | list[str] | None = None,
        formula_created_by: str | list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        exclude_hidden: bool | None = None,
        sort_by: str | None = None,
        order: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[WorksheetSearchItem]:
        """Search for formulas across Worksheets matching the given filters.

        Returns lightweight, partially populated
        [`WorksheetSearchItem`][albert.resources.worksheets.WorksheetSearchItem]
        results and is the fastest way to discover formulations across Projects and
        Sheets. Results are returned as a lazily paginated iterator. When you need
        the complete formula, pass a result's ``id`` to
        [`get_by_id`][albert.collections.inventory.InventoryCollection.get_by_id].

        !!! example
            ```python
            for hit in client.worksheets.search(text="cool formulation", max_items=10):
                print(hit.id, hit.name)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against formula fields.
        project_id : SearchProjectId, optional
            Scope the search to a Project (format ``PRO...``).
            The ``PRO`` prefix is stripped before the request is sent.
        sheet_id : str, optional
            Filter to formulas on a given Sheet.
        tags : str or list[str], optional
            Filter by tag name(s).
        albert_id : str or list[str], optional
            Filter by formula inventory ID(s) (format ``INV...``).
        state : str or list[str], optional
            Filter by formula state (e.g. locked or unlocked).
        predecessor : str or list[str], optional
            Filter by predecessor formula.
        data_template : str or list[str], optional
            Filter by data template name(s).
        inventory_name : str or list[str], optional
            Filter by ingredient name(s).
        inventory_id : str or list[str], optional
            Filter by ingredient inventory ID(s).
        formula_created_by : str or list[str], optional
            Filter by formula creator(s).
        facet_text : str, optional
            Text to match within a facet search.
        facet_field : str, optional
            Field to search within for facet filtering.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        exclude_hidden : bool, optional
            When True, omit hidden formulas from the results.
        sort_by : str, optional
            Field to sort results by.
        order : OrderBy, optional
            The order in which to sort results (``asc`` or ``desc``).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[WorksheetSearchItem]
            A lazily paginated iterator of matching formula search results.
        """
        params: dict[str, Any] = {
            "text": text,
            "projectId": project_id,
            "sheetId": sheet_id,
            "tags": ensure_list(tags),
            "albertId": ensure_list(albert_id),
            "state": ensure_list(state),
            "predecessor": ensure_list(predecessor),
            "dataTemplate": ensure_list(data_template),
            "inventoryName": ensure_list(inventory_name),
            "inventoryId": ensure_list(inventory_id),
            "formulaCreatedBy": ensure_list(formula_created_by),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "excludeHidden": exclude_hidden,
            "sortBy": sort_by,
            "order": order,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [WorksheetSearchItem.model_validate(x) for x in items],
        )

    @validate_call
    def setup_worksheet(self, *, project_id: ProjectId, add_sheet=False) -> Worksheet:
        """Initialize a Worksheet for a Project that does not yet have one.

        Most Projects already have a Worksheet; use this only when a Project's
        Worksheet has not been set up. To retrieve an existing Worksheet, use
        [`get_by_project_id`][albert.collections.worksheets.WorksheetCollection.get_by_project_id].

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            worksheet = client.worksheets.setup_worksheet(project_id="PROA9999999", add_sheet=True)
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project to set up the Worksheet for (format ``PRO...``).
        add_sheet : bool, optional
            When True, a blank Sheet is added to the new Worksheet. Default is False.

        Returns
        -------
        Worksheet
            The Worksheet for the Project.
        """

        params = {"sheets": str(add_sheet).lower()}
        path = f"{self.base_path}/{project_id}/setup"
        self.session.post(path, json=params)
        return self.get_by_project_id(project_id=project_id)

    @validate_call
    def setup_new_sheet_from_template(
        self, *, project_id: ProjectId, sheet_template_id: str, sheet_name: str
    ) -> Worksheet:
        """Add a new Sheet to a Project's Worksheet, built from a Sheet template.

        The template supplies the starting structure (columns and rows) for the
        new Sheet. Sheet templates are created with [`create_sheet_template`][albert.collections.worksheets.WorksheetCollection.create_sheet_template].

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            worksheet = client.worksheets.setup_new_sheet_from_template(
                project_id="PROA9999999",
                sheet_template_id="CTP123",
                sheet_name="Trial 1",
            )
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project whose Worksheet the Sheet is added to (format ``PRO...``).
        sheet_template_id : str
            The ID of the Sheet template to build the new Sheet from.
        sheet_name : str
            The name of the new Sheet.

        Returns
        -------
        Worksheet
            The Worksheet, now including the newly created Sheet.
        """
        payload = {"name": sheet_name}
        params = {"templateId": sheet_template_id}
        path = f"{self.base_path}/project/{project_id}/sheets"
        self.session.post(path, json=payload, params=params)
        return self.get_by_project_id(project_id=project_id)

    @validate_call
    def add_sheet(self, *, project_id: ProjectId, sheet_name: str) -> Worksheet:
        """Add a new blank Sheet to a Project's Worksheet.

        The new Sheet starts empty. To start from an existing structure instead,
        use [`setup_new_sheet_from_template`][albert.collections.worksheets.WorksheetCollection.setup_new_sheet_from_template] or [`duplicate_sheet`][albert.collections.worksheets.WorksheetCollection.duplicate_sheet].

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            worksheet = client.worksheets.add_sheet(project_id="PROA9999999", sheet_name="Trial 2")
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project whose Worksheet the Sheet is added to (format ``PRO...``).
        sheet_name : str
            The name of the new Sheet.

        Returns
        -------
        Worksheet
            The Worksheet, now including the newly created Sheet.
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
        """Copy an existing Sheet into a new Sheet within the same Project.

        The new Sheet is created from the named source Sheet. You control which
        Product Design rows and columns are carried over using the options below.
        The final set of columns copied is the union of:

        - all pinned columns (if ``copy_all_pinned_columns`` is True)
        - all unpinned columns (if ``copy_all_unpinned_columns`` is True)
        - explicitly listed column names (``column_names``)

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            worksheet = client.worksheets.duplicate_sheet(
                project_id="PROA9999999",
                source_sheet_name="Trial 1",
                new_sheet_name="Trial 1 (copy)",
            )
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project the source Sheet belongs to (format ``PRO...``).
        source_sheet_name : str
            The name of the existing Sheet to duplicate.
        new_sheet_name : str
            The name of the new Sheet to create.
        copy_all_pd_rows : bool, optional
            When True, all Product Design rows from the source Sheet are copied.
            When False, only rows corresponding to the selected columns are copied.
            Default is True.
        copy_all_pinned_columns : bool, optional
            When True, includes all pinned columns from the source Sheet. Default is True.
        copy_all_unpinned_columns : bool, optional
            When True, includes all unpinned columns from the source Sheet. Default is True.
        column_names : list[str], optional
            Column names to explicitly copy. These are resolved internally to column
            IDs using the source Sheet's Product Design grid.
        task_row_names : list[str], optional
            Names of task rows to include from the source Sheet's Tasks.

        Returns
        -------
        Worksheet
            The Worksheet, now including the newly created Sheet.
        """

        worksheet = self.get_by_project_id(project_id=project_id)
        sheet = get_sheet_from_worksheet(sheet_name=source_sheet_name, worksheet=worksheet)
        columns = get_columns_to_copy(
            sheet=sheet,
            copy_all_pinned_columns=copy_all_pinned_columns,
            copy_all_unpinned_columns=copy_all_unpinned_columns,
            input_column_names=column_names,
        )
        task_rows = get_task_rows_to_copy(sheet=sheet, input_row_names=task_row_names)

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

    @validate_call
    def create_sheet_template(
        self,
        *,
        project_id: ProjectId,
        source_sheet_name: str,
        template_name: str,
        copy_all_pd_rows: bool = True,
        copy_all_pinned_columns: bool = True,
        copy_all_unpinned_columns: bool = True,
        column_names: list[str] | None = None,
        task_row_names: list[str] | None = None,
        prg_row_names: list[str] | None = None,
        acl: ACLContainer | None = None,
    ) -> CustomTemplate:
        """Save an existing Sheet as a reusable Sheet template.

        The template captures the structure of the source Sheet so new Sheets can
        be built from it later with [`setup_new_sheet_from_template`][albert.collections.worksheets.WorksheetCollection.setup_new_sheet_from_template]. At least
        one column must be selected, or a ``ValueError`` is raised. The set of
        columns saved is the union of pinned columns, unpinned columns, and any
        explicitly listed ``column_names`` (per the flags below).

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            template = client.worksheets.create_sheet_template(
                project_id="PROA9999999",
                source_sheet_name="Trial 1",
                template_name="Standard trial layout",
            )
            ```

        Parameters
        ----------
        project_id : ProjectId
            The ID of the Project the source Sheet belongs to (format ``PRO...``).
        source_sheet_name : str
            The name of the existing Sheet to use as the template source.
        template_name : str
            The name of the new template.
        copy_all_pd_rows : bool, optional
            When True, all Product Design rows from the source Sheet are copied.
            When False, only rows corresponding to the selected columns are copied.
            Default is True.
        copy_all_pinned_columns : bool, optional
            When True, includes all pinned columns from the source Sheet. Default is True.
        copy_all_unpinned_columns : bool, optional
            When True, includes all unpinned columns from the source Sheet. Default is True.
        column_names : list[str], optional
            Column names to explicitly copy. These are resolved internally to column
            IDs using the source Sheet's Product Design grid.
        task_row_names : list[str], optional
            Names of task rows to include from the source Sheet's Tasks.
        prg_row_names : list[str], optional
            Names of parameter group rows to include.
        acl : ACLContainer, optional
            Access control settings for the template.

        Returns
        -------
        CustomTemplate
            The created Sheet template.

        Raises
        ------
        ValueError
            If no columns are selected to include in the template.
        """
        worksheet = self.get_by_project_id(project_id=project_id)
        sheet = get_sheet_from_worksheet(sheet_name=source_sheet_name, worksheet=worksheet)
        columns = get_columns_to_copy(
            sheet=sheet,
            copy_all_pinned_columns=copy_all_pinned_columns,
            copy_all_unpinned_columns=copy_all_unpinned_columns,
            input_column_names=column_names,
        )
        if not columns:
            raise ValueError("At least one column must be selected to create a template.")
        task_rows = get_task_rows_to_copy(sheet=sheet, input_row_names=task_row_names)
        prg_rows = get_prg_rows_to_copy(sheet=sheet, input_row_names=prg_row_names)

        payload = {
            "name": template_name,
            "sourceData": {
                "projectId": project_id,
                "sheetId": sheet.id,
                "Columns": [{"id": col_id} for col_id in columns],
                "copyAllPDRows": copy_all_pd_rows,
                "TaskRows": [{"id": row_id} for row_id in task_rows],
                "PRGRows": [{"id": row_id} for row_id in prg_rows],
            },
        }

        if acl is not None:
            payload["ACL"] = acl.model_dump(exclude_none=True, by_alias=True, mode="json")

        path = f"{self.base_path}/sheet/template"
        response = self.session.post(path, json=payload)
        response_json = response.json()
        ctp_id = response_json.get("ctpId")
        return CustomTemplatesCollection(session=self.session).get_by_id(id=ctp_id)
