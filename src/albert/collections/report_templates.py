from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.report_templates import (
    ReportTemplate,
    ReportTemplateCategory,
)


class ReportTemplateCollection(BaseCollection):
    """ReportTemplateCollection is a collection class for managing ReportTemplate entities in the Albert platform.

    This collection provides methods to retrieve and list report templates.
    Report templates define the structure and configuration for generating reports in Albert.


    """

    _api_version = "v3"
    _updatable_attributes = {}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the ReportTemplateCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ReportTemplateCollection._api_version}/reporttemplates"

    def get_by_id(self, *, id: str) -> ReportTemplate:
        """
        Retrieve a report template by its ID.

        Parameters
        ----------
        id : str
            The ID of the report template to retrieve.

        Returns
        -------
        ReportTemplate
            The report template with the given ID.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return ReportTemplate(**response.json())

    def get_all(
        self,
        *,
        category: ReportTemplateCategory | None = None,
    ) -> list[ReportTemplate]:
        """
        Retrieve all report templates with optional filtering.

        Parameters
        ----------
        category : ReportTemplateCategory | None, optional
            Filter by report template category, by default None

        Yields
        ------
        ReportTemplate
            Report template objects.
        """
        params = {}
        if category:
            params["category"] = category

        # This microservice has no pagination
        response = self.session.get(self.base_path, params=params)
        return [ReportTemplate(**item) for item in response.json()["Items"]]
