from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ProjectId
from albert.core.utils import ensure_list
from albert.resources.targets import Target


class TargetCollection(BaseCollection):
    """
    TargetCollection is a collection class for managing Target entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for target API requests.

    Methods
    -------
    create(target) -> Target
        Creates a new target entity.
    get_by_id(id) -> Target
        Retrieves a target by its ID.
    list(project_id=None) -> list[Target]
        Lists target entities with an optional project ID filter.
    delete(id) -> None
        Deletes a target by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the TargetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TargetCollection._api_version}/targets"

    def create(self, *, target: Target) -> Target:
        """
        Creates a new target entity.

        Parameters
        ----------
        target : Target
            The target object to create.

        Returns
        -------
        Target
            The created Target entity.
        """
        response = self.session.post(
            self.base_path,
            json=target.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Target(**response.json())

    def get_by_id(self, *, id: str) -> Target:
        """
        Retrieves a target by its ID.

        Parameters
        ----------
        id : str
            The ID of the target to retrieve.

        Returns
        -------
        Target
            The Target entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Target(**response.json())

    def list(self, *, project_id: ProjectId | None = None) -> list[Target]:
        """
        Lists target entities with an optional project ID filter.

        Parameters
        ----------
        project_id : ProjectId | None
            One or more project IDs to filter targets by.

        Returns
        -------
        list[Target]
            A list of Target entities.
        """
        params = {}
        if project_id is not None:
            params["projectId"] = ensure_list(project_id)
        response = self.session.get(self.base_path, params=params)
        data = response.json()
        return [Target(**item) for item in data.get("Items", [])]

    def delete(self, *, id: str) -> None:
        """
        Deletes a target by its ID.

        Parameters
        ----------
        id : str
            The ID of the target to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
