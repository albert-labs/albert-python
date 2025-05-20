from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.projects import Project
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ProjectCollection(BaseCollection):
    """ProjectCollection is a collection class for managing Project entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"description", "grid", "metadata", "state"}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize a ProjectCollection object.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ProjectCollection._api_version}/projects"

    def create(self, *, project: Project) -> Project:
        """
        Create a new project.

        Parameters
        ----------
        project : Project
            The project to create.

        Returns
        -------
        Optional[Project]
            The created project object if successful, None otherwise.
        """
        response = self.session.post(
            self.base_path, json=project.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Project(**response.json())

    def get_by_id(self, *, id: str) -> Project:
        """
        Retrieve a project by its ID.

        Parameters
        ----------
        id : str
            The ID of the project to retrieve.

        Returns
        -------
        Project
            The project object if found
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)

        return Project(**response.json())

    def update(self, *, project: Project) -> Project:
        """Update a project.

        Parameters
        ----------
        project : Project
            The updated project object.

        Returns
        -------
        Project
            The updated project object as returned by the server.
        """
        existing_project = self.get_by_id(id=project.id)
        patch_data = self._generate_patch_payload(existing=existing_project, updated=project)
        url = f"{self.base_path}/{project.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=project.id)

    def delete(self, *, id: str) -> None:
        """
        Delete a project by its ID.

        Parameters
        ----------
        id : str
            The ID of the project to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def list(
        self,
        *,
        text: str = None,
        status: list[str] = None,
        market_segment: list[str] = None,
        application: list[str] = None,
        technology: list[str] = None,
        created_by: list[str] = None,
        location: list[str] = None,
        from_created_at: str = None,
        to_created_at: str = None,
        facet_field: str = None,
        facet_text: str = None,
        contains_field: list[str] = None,
        contains_text: list[str] = None,
        linked_to: str = None,
        my_projects: bool = None,
        my_role: list[str] = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str = None,
        limit: int = 50,
    ) -> Iterator[Project]:
        """
        List projects with optional filters.

        Parameters
        ----------
        text : str, optional
            Search any test in the project.
        status : list[str], optional
            The status filter for the projects.
        market_segment : list[str], optional
            The market segment filter for the projects.
        application : list[str], optional
            The application filter for the projects.
        technology : list[str], optional
            The technology filter for the projects.
        created_by : list[str], optional
            The name of the user who created the project.
        location : list[str], optional
            The location filter for the projects.
        from_created_at : str, optional
            The start date filter for the projects.
        to_created_at : str, optional
            The end date filter for the projects.
        facet_field : str, optional
            The facet field for the projects.
        facet_text : str, optional
            The facet text for the projects.
        contains_field : list[str], optional
            To power project facets search
        contains_text : list[str], optional
            To power project facets search
        linked_to : str, optional
            To pass text for linked to dropdown search in Task creation flow.
        my_projects : bool, optional
            Return Projects owned by you.
        my_role : list[str], optional
            Filter Projects to ones which you have a specific role in.
        order_by : OrderBy, optional
            The order in which to retrieve items (default is OrderBy.DESCENDING).
        sort_by : str, optional
            The field to sort by.

        Returns
        ------
        Iterator[Project]
            An iterator of Project resources.
        """
        params = {
            "limit": limit,
            "order": order_by.value,
            "text": text,
            "sortBy": sort_by,
            "status": status,
            "marketSegment": market_segment,
            "application": application,
            "technology": technology,
            "createdBy": created_by,
            "location": location,
            "fromCreatedAt": from_created_at,
            "toCreatedAt": to_created_at,
            "facetField": facet_field,
            "facetText": facet_text,
            "containsField": contains_field,
            "containsText": contains_text,
            "linkedTo": linked_to,
            "myProjects": my_projects,
            "myRole": my_role,
        }
        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=lambda items: [Project(**item) for item in items],
        )
