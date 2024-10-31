from albert.collections.base import BaseCollection
from albert.resources.reports import ReportInfo
from albert.session import AlbertSession


class ReportCollection(BaseCollection):
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

    def get_datascience_report(
        self,
        *,
        report_type_id: str,
        project_ids: list[str],
        unique_ids: list[str] | None = None,
    ) -> ReportInfo:
        """Get a datascience report by its report type ID.

        Parameters
        ----------
        report_type_id : str
            The report type ID for the report.
        project_ids : list[str]
            Project IDs to query on the input data.
        unique_ids : list[str] | None
            Optional unique IDs to query on the input data.

        Returns
        -------
        ReportInfo
            The info for the report.
        """
        path = f"{self.base_path}/datascience/{report_type_id}"
        params = {"inputData[projectId]": project_ids}
        if unique_ids is not None:
            params["inputData[uniqueId]"] = unique_ids
        response = self.session.get(path, params=params)
        return ReportInfo(**response.json())
