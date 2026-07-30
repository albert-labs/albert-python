from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ReportId
from albert.resources.reports import FullAnalyticalReport, ReportInfo


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
    def get_full_report(self, *, report_id: ReportId) -> FullAnalyticalReport:
        """Get a saved analytical report by its ID.

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
