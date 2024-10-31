from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.projects import Project
from albert.session import AlbertSession


class ProjectCollection(BaseCollection):
    """
    ProjectCollection is a collection class for managing project entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for project API requests.

    Methods
    -------
    create(project: Project) -> Optional[str]
        Creates a new project.
    get_by_id(project_id: str) -> Optional[dict]
        Retrieves a project by its ID.
    update(project_id: str, patch_data: dict) -> bool
        Updates a project by its ID.
    delete(project_id: str) -> bool
        Deletes a project by its ID.
    list(name: Optional[List[str]], category: Optional[str], order_by: OrderBy, exact_match: bool) -> Generator
        Lists projects with optional filters.
    """

    _api_version = "v3"
    _updatable_attributes = {"description", "grid", "metadata"}

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

    def create(self, *, project: Project) -> Project | None:
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
            self.base_path, json=project.model_dump(by_alias=True, exclude_unset=True)
        )

        return Project(**response.json())

    def get_by_id(self, *, project_id: str) -> Project:
        """
        Retrieve a project by its ID.

        Parameters
        ----------
        project_id : str
            The ID of the project to retrieve.

        Returns
        -------
        Project
            The project object if found
        """
        url = f"{self.base_path}/{project_id}"
        response = self.session.get(url)

        return Project(**response.json())

    def update(self, *, updated_project: Project) -> Project:
        """
        TO DO: This needs some more custom patch logic
        """
        existing_project = self.get_by_id(project_id=updated_project.id)
        patch_data = self._generate_patch_payload(
            existing=existing_project, updated=updated_project
        )
        url = f"{self.base_path}/{updated_project.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return updated_project

    def delete(self, *, project_id: str) -> None:
        """
        Delete a project by its ID.

        Parameters
        ----------
        project_id : str
            The ID of the project to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{project_id}"
        self.session.delete(url)

    def _list_generator(
        self,
        *,
        limit: int = 50,
        start_key: str = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Generator[Project, None, None]:
        """
        Generator for listing projects with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of items to retrieve per request (default is 50).
        start_key : Union[str, None], optional
            The start key for pagination.
        name : Optional[List[str]], optional
            The name filter for the projects.
        order_by : OrderBy, optional
            The order in which to retrieve items (default is OrderBy.DESCENDING).
        exact_match : bool, optional
            Whether to match names exactly (default is False).

        Yields
        ------
        Project
            The next project in the generator.
        """
        params = {
            "limit": str(limit),
            "orderBy": order_by.value,
        }
        if start_key:  # pragma: no cover
            params["startKey"] = start_key
        while True:
            response = self.session.get(self.base_path, params=params)

            raw_projects = response.json().get("Items", [])
            if not raw_projects or raw_projects == []:  # pragma: no cover
                break
            for x in raw_projects:
                yield Project(**x)
            start_key = response.json().get("lastKey")
            if not start_key or len(raw_projects) < limit:
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Iterator[Project]:
        """
        List projects with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order in which to retrieve items (default is OrderBy.DESCENDING).
        Returns
        -------
        Generator
            A generator yielding projects that match the filters.
        """
        return self._list_generator(order_by=order_by)
