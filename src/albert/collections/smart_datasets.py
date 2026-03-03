from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId
from albert.resources.smart_datasets import SmartDataset, SmartDatasetScope


class SmartDatasetCollection(BaseCollection):
    """
    SmartDatasetCollection is a collection class for managing SmartDataset entities
    in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for smart dataset API requests.

    Methods
    -------
    create(scope, build=True) -> SmartDataset
        Creates a new smart dataset entity.
    get_all() -> list[SmartDataset]
        Lists all smart datasets for the tenant.
    get_by_id(id) -> SmartDataset
        Retrieves a smart dataset by its ID.
    update(id, **kwargs) -> SmartDataset
        Updates a smart dataset by its ID.
    delete(id) -> None
        Deletes a smart dataset by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the SmartDatasetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SmartDatasetCollection._api_version}/smartdatasets"

    def create(
        self,
        *,
        scope: SmartDatasetScope,
        build: bool = True,
    ) -> SmartDataset:
        """
        Creates a new smart dataset entity.

        Parameters
        ----------
        scope : SmartDatasetScope
            The scope of the smart dataset.
        build : bool, optional
            Whether to populate the smart dataset with data from Albert.

        Returns
        -------
        SmartDataset
            The created smart dataset entity.
        """
        response = self.session.post(
            self.base_path,
            json={"scope": scope.model_dump(by_alias=True, exclude_none=False, mode="json")},
            params={"build": build},
        )
        return SmartDataset(**response.json())

    def get_all(self) -> list[SmartDataset]:
        """
        Lists all smart datasets for the tenant.

        Returns
        -------
        list[SmartDataset]
            A list of SmartDataset entities.
        """
        response = self.session.get(self.base_path)
        data = response.json()
        return [SmartDataset(**item) for item in data.get("Items", [])]

    def get_by_id(self, *, id: SmartDatasetId) -> SmartDataset:
        """
        Retrieves a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to retrieve.

        Returns
        -------
        SmartDataset
            The SmartDataset entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return SmartDataset(**response.json())

    def update(self, *, smart_dataset: SmartDataset) -> SmartDataset:
        """
        Updates a smart dataset by its ID.

        Parameters
        ----------
        smart_dataset : SmartDataset
            The smart dataset to update. Must have an id set.

        Returns
        -------
        SmartDataset
            The updated SmartDataset entity.
        """
        url = f"{self.base_path}/{smart_dataset.id}"
        payload = smart_dataset.model_dump(
            by_alias=True,
            exclude_none=True,
            mode="json",
            include={"status", "storage_key", "scope", "schema_"},
        )
        response = self.session.patch(url, json=payload)
        return SmartDataset(**response.json())

    def delete(self, *, id: SmartDatasetId) -> None:
        """
        Deletes a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
