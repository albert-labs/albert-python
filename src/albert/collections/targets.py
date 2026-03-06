from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import TargetId
from albert.resources.targets import Target


class TargetCollection(BaseCollection):
    """A collection for managing targets in the Albert platform (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

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
    get_by_ids(ids) -> list[Target]
        Fetches multiple targets at once by their IDs.
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

    def get_by_id(self, *, id: TargetId) -> Target:
        """
        Retrieves a target by its ID.

        Parameters
        ----------
        id : TargetId
            The ID of the target to retrieve.

        Returns
        -------
        Target
            The Target entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Target(**response.json())

    def get_by_ids(self, *, ids: list[TargetId]) -> list[Target]:
        """
        Fetches multiple targets at once by their IDs.

        Parameters
        ----------
        ids : list[TargetId]
            The IDs of the targets to fetch.

        Returns
        -------
        list[Target]
            A list of Target entities.
        """
        url = f"{self.base_path}/ids"
        response = self.session.get(url, params={"id": ids})
        data = response.json()
        return [Target(**item) for item in data.get("Items", [])]

    def delete(self, *, id: TargetId) -> None:
        """
        Deletes a target by its ID.

        Parameters
        ----------
        id : TargetId
            The ID of the target to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
