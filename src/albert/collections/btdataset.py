from albert.collections.base import BaseCollection
from albert.resources.btdataset import BTDataset
from albert.session import AlbertSession


class BTDatasetCollection(BaseCollection):
    """
    BTDatasetCollection is a collection class for managing Breakthrough dataset entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base path for btdataset API requests.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "key", "file_name"}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the BTDatasetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BTDatasetCollection._api_version}/btdataset"

    def create(self, *, dataset: BTDataset) -> BTDataset:
        """
        Create a new BTDataset.

        Parameters
        ----------
        dataset : BTDataset
            The BTDataset record to create.

        Returns
        -------
        BTDataset
            The created BTDataset.
        """
        response = self.session.post(
            self.base_path,
            json=dataset.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTDataset(**response.json())

    def get_by_id(self, *, id: str) -> BTDataset:
        """
        Get a BTDataset by ID.

        Parameters
        ----------
        id : str
            The Albert ID of the BTDataset.

        Returns
        -------
        BTDataset
            The retrived BTDataset.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTDataset(**response.json())

    def update(self, *, dataset: BTDataset) -> BTDataset:
        """
        Update a BTDataset.

        The provided dataset must be registered with an Albert ID.

        Parameters
        ----------
        dataset : BTDataset
            The BTDataset with updated fields.

        Returns
        -------
        BTDataset
            The updated BTDataset object.
        """
        path = f"{self.base_path}/{dataset.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=dataset.id),
            updated=dataset,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=dataset.id)
