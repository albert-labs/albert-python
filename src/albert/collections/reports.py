from typing import Any

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ReportId
from albert.resources.reports import FullAnalyticalReport, ReportInfo


class ReportCollection(BaseCollection):
    """ReportCollection is a collection class for managing Report entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the ReportCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ReportCollection._api_version}/reports"

    def get_report(
        self, *, category: str, report_type_id: str, input_data: dict[str, Any] | None = None
    ) -> ReportInfo:
        """Get a report by its category and report type ID.

        Parameters
        ----------
        category : str
            The category of the report (e.g., "datascience", "analytics", etc...).
        report_type_id : str
            The report type ID for the report.
        input_data : dict[str, Any] | None
            Additional input data for generating the report
            (e.g., project IDs and unique IDs).

        Returns
        -------
        ReportInfo
            The info for the report.

        Examples
        --------
        >>> report = client.reports.get_report(
        ...     category="datascience",
        ...     report_type_id="ALB#RET51",
        ...     input_data={
        ...         "project": ["PRO123"],
        ...     }
        ... )
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
        """Get an analytics report by its report type ID.

        Parameters
        ----------
        report_type_id : str
            The report type ID for the report.
        input_data : dict[str, Any] | None
            Additional input data for generating the report
            (e.g., project IDs and unique IDs).

        Returns
        -------
        ReportInfo
            The info for the report.

        Examples
        --------
        >>> report = client.reports.get_analytics_report(
        ...     report_type_id="RET22",
        ...     input_data={
        ...         "inventoryId": "INVA123"
        ...     }
        ... )
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
        """Get a datascience report by its report type ID.

        Parameters
        ----------
        report_type_id : str
            The report type ID for the report.
        input_data : dict[str, Any] | None
            Additional input data for generating the report
            (e.g., project IDs and unique IDs).

        Returns
        -------
        ReportInfo
            The info for the report.

        Examples
        --------
        >>> report = client.reports.get_datascience_report(
        ...     report_type_id="RET51",
        ...     input_data={
        ...         "projectId": ["PRO123"],
        ...         "uniqueId": ["DAT123_DAC123"]
        ...     }
        ... )
        """
        return self.get_report(
            category="datascience",
            report_type_id=report_type_id,
            input_data=input_data,
        )

    def get_full_report(self, *, report_id: ReportId) -> FullAnalyticalReport:
        """Get a full analytical report by its ID.

        Parameters
        ----------
        report_id : ReportId
            The ID of the report to retrieve.

        Returns
        -------
        FullAnalyticalReport
            The full analytical report with all configuration and data.

        Examples
        --------
        >>> report = client.reports.get_full_report(report_id="REP14")
        >>> report_dataframe = report.get_raw_dataframe()
        """
        path = f"{self.base_path}/{report_id}"
        params = {"viewReport": "1"}

        response = self.session.get(path, params=params)
        return FullAnalyticalReport(**response.json())

    def create_report(self, *, report: FullAnalyticalReport) -> FullAnalyticalReport:
        """Create a new analytical report.

        Parameters
        ----------
        report : FullAnalyticalReport
            The report configuration to create.

        Returns
        -------
        FullAnalyticalReport
            The created report with the generated report_data_id.

        Examples
        --------
        >>> new_report = FullAnalyticalReport(
        ...     report_type_id="ALB#RET22",
        ...     name="My New Report",
        ...     description="A test report"
        ... )
        >>> created_report = client.reports.create_report(report=new_report)
        """
        path = self.base_path

        # Prepare the data for creation (exclude read-only fields)
        report_data = report.model_dump(
            exclude={"report_data_id", "created_by", "report"}, exclude_none=True, by_alias=True
        )

        response = self.session.post(path, json=report_data)
        return FullAnalyticalReport(**response.json())

    def delete(self, *, id: ReportId) -> None:
        """Delete a report.

        Parameters
        ----------
        id : ReportId
            The ID of the report to delete.

        Examples
        --------
        >>> client.reports.delete(id="REP14")
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)
