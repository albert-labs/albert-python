from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ProjectId, ReportId
from albert.core.utils import ensure_list
from albert.resources.reports import FullAnalyticalReport, ReportInfo, ReportSearchItem


class ReportCollection(BaseCollection):
    """Manage Reports in the Albert platform.

    A Report runs a predefined server-side report type over the data you point it
    at and returns the computed results. Report types fall into categories such as
    ``"analytics"`` and ``"datascience"``, and each is identified by a report type
    ID (e.g. ``"RET22"`` or the fully qualified ``"ALB#RET51"``). The set of
    available report types is defined by Report Templates (see
    [`ReportTemplateCollection`][albert.collections.report_templates.ReportTemplateCollection]).

    Two styles of access are provided:

    - Run a report on demand and read its results directly with
      [`get_report`][albert.collections.reports.ReportCollection.get_report] (or the category-specific [`get_analytics_report`][albert.collections.reports.ReportCollection.get_analytics_report]
      and [`get_datascience_report`][albert.collections.reports.ReportCollection.get_datascience_report]). These take ``input_data`` describing
      what to run the report over (e.g. project or inventory IDs).
    - Persist a report configuration as a [`FullAnalyticalReport`][albert.resources.reports.FullAnalyticalReport]
      with [`create_report`][albert.collections.reports.ReportCollection.create_report], then fetch it later by its Report ID (format
      ``REP...``) with [`get_full_report`][albert.collections.reports.ReportCollection.get_full_report].

    This collection is accessed as ``client.reports``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        report = client.reports.get_datascience_report(
            report_type_id="RET51",
            input_data={"projectId": ["PRO123"], "uniqueId": ["DAT123_DAC123"]},
        )
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for report requests.

    Methods
    -------
    get_report(category, report_type_id, input_data=None) -> ReportInfo
        Run a report of any category and return its results.
    get_analytics_report(report_type_id, input_data=None) -> ReportInfo
        Run an analytics report and return its results.
    get_datascience_report(report_type_id, input_data=None) -> ReportInfo
        Run a datascience report and return its results.
    search(...) -> Iterator[ReportSearchItem]
        Search for saved reports matching the given filters.
    get_full_report(report_id) -> FullAnalyticalReport
        Get a saved report by its ID, with configuration and data.
    create_report(report) -> FullAnalyticalReport
        Persist a new analytical report configuration.
    delete(id) -> None
        Delete a saved report by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a ReportCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ReportCollection._api_version}/reports"

    def get_report(
        self, *, category: str, report_type_id: str, input_data: dict[str, Any] | None = None
    ) -> ReportInfo:
        """Run a report of a given category and return its results.

        !!! example
            ```python
            report = client.reports.get_report(
                category="datascience",
                report_type_id="ALB#RET51",
                input_data={"project": ["PRO123"]},
            )
            ```

        Parameters
        ----------
        category : str
            The category of the report (e.g. ``"datascience"`` or ``"analytics"``).
        report_type_id : str
            The report type ID identifying which report to run (e.g. ``"RET51"``
            or the fully qualified ``"ALB#RET51"``).
        input_data : dict[str, Any] | None
            Input describing what to run the report over, keyed by field name
            (e.g. project IDs, inventory IDs, or unique IDs). Optional.

        Returns
        -------
        ReportInfo
            The report type metadata and computed result items.
        """
        path = f"{self.base_path}/{category}/{report_type_id}"

        params = {}
        input_data = input_data or {}
        for key, value in input_data.items():
            params[f"inputData[{key}]"] = value

        response = self.session.get(path, params=params)
        return ReportInfo(**response.json())

    def get_analytics_report(
        self,
        *,
        report_type_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> ReportInfo:
        """Run an analytics report and return its results.

        Convenience wrapper around [`get_report`][albert.collections.reports.ReportCollection.get_report] with
        ``category="analytics"``.

        !!! example
            ```python
            report = client.reports.get_analytics_report(
                report_type_id="RET22",
                input_data={"inventoryId": "INVA123"},
            )
            ```

        Parameters
        ----------
        report_type_id : str
            The report type ID identifying which analytics report to run
            (e.g. ``"RET22"``).
        input_data : dict[str, Any] | None
            Input describing what to run the report over, keyed by field name
            (e.g. inventory IDs). Optional.

        Returns
        -------
        ReportInfo
            The report type metadata and computed result items.
        """
        return self.get_report(
            category="analytics",
            report_type_id=report_type_id,
            input_data=input_data,
        )

    def get_datascience_report(
        self,
        *,
        report_type_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> ReportInfo:
        """Run a datascience report and return its results.

        Convenience wrapper around [`get_report`][albert.collections.reports.ReportCollection.get_report] with
        ``category="datascience"``.

        !!! example
            ```python
            report = client.reports.get_datascience_report(
                report_type_id="RET51",
                input_data={
                    "projectId": ["PRO123"],
                    "uniqueId": ["DAT123_DAC123"],
                },
            )
            ```

        Parameters
        ----------
        report_type_id : str
            The report type ID identifying which datascience report to run
            (e.g. ``"RET51"``).
        input_data : dict[str, Any] | None
            Input describing what to run the report over, keyed by field name
            (e.g. project IDs and unique IDs). Optional.

        Returns
        -------
        ReportInfo
            The report type metadata and computed result items.
        """
        return self.get_report(
            category="datascience",
            report_type_id=report_type_id,
            input_data=input_data,
        )

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        created_by: str | None = None,
        project_id: ProjectId | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        report_type: str | list[str] | None = None,
        created_by_name: str | list[str] | None = None,
        linked_to: str | list[str] | None = None,
        shared_with: str | list[str] | None = None,
        source_field: str | list[str] | None = None,
        additional_field: str | list[str] | None = None,
        sort_by: str | None = None,
        order: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[ReportSearchItem]:
        """Search for saved reports matching the given filters.

        Returns lightweight, partial [`ReportSearchItem`][albert.resources.reports.ReportSearchItem]
        results. Call ``hydrate()`` on a result to fetch the fully populated
        [`FullAnalyticalReport`][albert.resources.reports.FullAnalyticalReport].

        All filters are optional; with no arguments this iterates over all saved
        reports you can access.

        !!! example
            ```python
            for hit in client.reports.search(text="solubility", max_items=25):
                print(hit.id, hit.name)
            ```

        Parameters
        ----------
        text : str, optional
            Full-text search query.
        created_by : str, optional
            Filter by creator User ID.
        project_id : ProjectId, optional
            Filter to reports scoped to a project (format ``PRO...``).
        facet_text : str, optional
            Facet text to search for.
        facet_field : str, optional
            Facet field to filter on.
        contains_field : str or list[str], optional
            Fields to search inside.
        contains_text : str or list[str], optional
            Values to search for within the ``contains_field``.
        report_type : str or list[str], optional
            Filter by report type name(s).
        created_by_name : str or list[str], optional
            Filter by creator display name(s).
        linked_to : str or list[str], optional
            Filter by linked entity or project ID(s).
        shared_with : str or list[str], optional
            Filter by user(s) the report is shared with.
        source_field : str or list[str], optional
            Restrict which fields are returned in the response.
        additional_field : str or list[str], optional
            Request additional fields from the search index.
        sort_by : str, optional
            Field to sort by.
        order : OrderBy, optional
            Sort order (``asc`` or ``desc``).
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[ReportSearchItem]
            An iterator of matching partial (unhydrated) report results.
        """
        payload: dict[str, Any] = {
            "text": text,
            "createdBy": created_by,
            "projectId": project_id,
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "reportType": ensure_list(report_type),
            "createdByName": ensure_list(created_by_name),
            "linkedTo": ensure_list(linked_to),
            "sharedWith": ensure_list(shared_with),
            "sourceField": ensure_list(source_field),
            "additionalField": ensure_list(additional_field),
            "sortBy": sort_by,
            "order": order,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            method="POST",
            json=payload,
            max_items=max_items,
            deserialize=lambda items: [
                ReportSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    @validate_call
    def get_full_report(self, *, report_id: ReportId) -> FullAnalyticalReport:
        """Get a saved analytical report by its ID.

        To find saved reports without knowing their IDs, use
        [`search`][albert.collections.reports.ReportCollection.search].

        !!! example
            ```python
            report = client.reports.get_full_report(report_id="REP14")
            report_dataframe = report.get_raw_dataframe()
            ```

        Parameters
        ----------
        report_id : ReportId
            The Report ID to retrieve (format ``REP...``).

        Returns
        -------
        FullAnalyticalReport
            The saved report with all of its configuration and data.
        """
        path = f"{self.base_path}/{report_id}"
        params = {"viewReport": "1"}

        response = self.session.get(path, params=params)
        return FullAnalyticalReport(**response.json())

    def create_report(self, *, report: FullAnalyticalReport) -> FullAnalyticalReport:
        """Create a new analytical report.

        Read-only fields on the supplied report (``report_data_id``,
        ``created_by``, and ``report``) are ignored on creation.

        !!! example
            ```python
            from albert.resources.reports import FullAnalyticalReport

            new_report = FullAnalyticalReport(
                report_type_id="ALB#RET22",
                name="My New Report",
                description="A test report",
            )
            created_report = client.reports.create_report(report=new_report)
            ```

        Parameters
        ----------
        report : FullAnalyticalReport
            The report configuration to create.

        Returns
        -------
        FullAnalyticalReport
            The created report as returned by the server, including its assigned
            ID.
        """
        path = self.base_path

        # Prepare the data for creation (exclude read-only fields)
        report_data = report.model_dump(
            exclude={"report_data_id", "created_by", "report"}, exclude_none=True, by_alias=True
        )

        response = self.session.post(path, json=report_data)
        return FullAnalyticalReport(**response.json())

    @validate_call
    def delete(self, *, id: ReportId) -> None:
        """Delete a saved report by its ID.

        !!! example
            ```python
            client.reports.delete(id="REP14")
            ```

        Parameters
        ----------
        id : ReportId
            The Report ID to delete (format ``REP...``).

        Returns
        -------
        None
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)
