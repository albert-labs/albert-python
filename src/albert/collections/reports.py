from typing import Any

from albert.collections.base import BaseCollection
from albert.resources.reports import ReportInfo
from albert.session import AlbertSession


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
        ...     report_type_id="RET51",
        ...     input_data={
        ...         "projectId": ["PRO123"],
        ...         "uniqueId": ["DAT123_DAC123"]
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
