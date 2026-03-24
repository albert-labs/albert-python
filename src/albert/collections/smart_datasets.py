from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId
from albert.resources.smart_datasets import SmartDataset, SmartDatasetScope


class SmartDatasetCollection(BaseCollection):
    """A collection for managing smart datasets in the Albert platform (🧪Beta).

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
        The base URL for smart dataset API requests.

    Methods
    -------
    create(scope, build=True) -> SmartDataset
        Creates a new smart dataset entity.
    get_all() -> list[SmartDataset]
        Lists all smart datasets for the tenant.
    get_by_id(id) -> SmartDataset
        Retrieves a smart dataset by its ID.
    update(smart_dataset, build=True) -> SmartDataset
        Updates a smart dataset.
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

    def _smart_dataset_patch_payload(
        self, *, existing: SmartDataset, updated: SmartDataset
    ) -> dict:
        """Build the PATCH request body by diffing the existing and updated smart datasets.

        Parameters
        ----------
        existing : SmartDataset
            The current server state.
        updated : SmartDataset
            The desired state.

        Returns
        -------
        dict
            The PATCH payload containing only changed fields.
        """
        payload: dict = {}
        if existing.scope != updated.scope and updated.scope is not None:
            payload["scope"] = updated.scope.model_dump(
                by_alias=True, exclude_none=False, mode="json"
            )
        if existing.build_state != updated.build_state and updated.build_state is not None:
            payload["buildState"] = updated.build_state.value
        if existing.storage_key != updated.storage_key and updated.storage_key is not None:
            payload["storageKey"] = updated.storage_key
        if existing.schema_ != updated.schema_ and updated.schema_ is not None:
            payload["schema"] = updated.schema_
        return payload

    def update(
        self,
        *,
        smart_dataset: SmartDataset,
    ) -> SmartDataset:
        """
        Update a smart dataset.

        Parameters
        ----------
        smart_dataset : SmartDataset
            The smart dataset with updated fields. Must have an id set.

        Returns
        -------
        SmartDataset
            The updated SmartDataset.
        """
        existing = self.get_by_id(id=smart_dataset.id)
        payload = self._smart_dataset_patch_payload(existing=existing, updated=smart_dataset)
        self.session.patch(
            url=f"{self.base_path}/{smart_dataset.id}",
            json=payload,
        )
        return self.get_by_id(id=smart_dataset.id)

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
