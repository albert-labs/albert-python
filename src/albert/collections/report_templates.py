from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.report_templates import (
    ReportTemplate,
    ReportTemplateCategory,
)


class ReportTemplateCollection(BaseCollection):
    """Manage Report Templates in the Albert platform.

    A Report Template defines a reusable report configuration: the report type it
    is based on, its available filters, and its default column, chart, and
    metadata state. Templates are the catalog of report types that can be run via
    [`ReportCollection`][albert.collections.reports.ReportCollection]. Each template belongs
    to a [`ReportTemplateCategory`][albert.resources.report_templates.ReportTemplateCategory]
    (``analytics``, ``datascience``, or ``reports``).

    This collection is read-only: it retrieves and lists existing templates.

    This collection is accessed as ``client.report_templates``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for report template requests.

    Methods
    -------
    get_by_id(id) -> ReportTemplate
        Retrieve a single report template by its ID.
    get_all(category=None) -> list[ReportTemplate]
        List all report templates, optionally filtered by category.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.report_templates import ReportTemplateCategory

        client = Albert()
        templates = client.report_templates.get_all(
            category=ReportTemplateCategory.ANALYTICS
        )
        for template in templates:
            print(template.id, template.name)
        ```
    """

    _api_version = "v3"
    _updatable_attributes = {}

    def __init__(self, *, session: AlbertSession):
        """Initialize a ReportTemplateCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ReportTemplateCollection._api_version}/reporttemplates"

    def get_by_id(self, *, id: str) -> ReportTemplate:
        """Retrieve a single report template by its ID.

        Parameters
        ----------
        id : str
            The ID of the report template to retrieve.

        Returns
        -------
        ReportTemplate
            The requested report template.

        !!! example
            ```python
            template = client.report_templates.get_by_id(id="...")
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return ReportTemplate(**response.json())

    def get_all(
        self,
        *,
        category: ReportTemplateCategory | None = None,
    ) -> list[ReportTemplate]:
        """List all report templates, optionally filtered by category.

        Parameters
        ----------
        category : ReportTemplateCategory | None, optional
            Restrict the results to a single template category. If omitted, all
            categories are returned.

        Returns
        -------
        list[ReportTemplate]
            The matching report templates.

        !!! example
            ```python
            from albert.resources.report_templates import ReportTemplateCategory

            templates = client.report_templates.get_all(
                category=ReportTemplateCategory.DATASCIENCE
            )
            ```
        """
        params = {}
        if category:
            params["category"] = category

        # This microservice has no pagination
        response = self.session.get(self.base_path, params=params)
        return [ReportTemplate(**item) for item in response.json()["Items"]]
