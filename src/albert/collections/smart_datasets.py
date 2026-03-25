from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
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

    _updatable_attributes = {"scope", "build_state", "storage_key", "schema_"}

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
        payload = self._generate_patch_payload(existing=existing, updated=smart_dataset)
        self.session.patch(
            url=f"{self.base_path}/{smart_dataset.id}",
            json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
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

    def _generate_patch_payload(
        self,
        *,
        existing: SmartDataset,
        updated: SmartDataset,
    ) -> PatchPayload:
        data = []
        for attribute in self._updatable_attributes:
            old_value = getattr(existing, attribute, None)
            new_value = getattr(updated, attribute, None)
            # Sometimes None and empty lists/dicts are serilized/deserilized to the same value, but wont look the same here
            if old_value is None and (new_value == [] or new_value == {}):
                # Avoid updating None to an empty list
                new_value = None
            elif (old_value == [] or old_value == {}) and new_value is None:
                # Avoid updating an empty list to None
                old_value = None

            # Get the serialization alias name for the attribute, if it exists
            field_info = existing.__class__.model_fields[attribute]
            alias = (
                getattr(field_info, "serialization_alias", None) or field_info.alias or attribute
            )

            if new_value != old_value:
                # Update existing attribute
                data.append(
                    PatchDatum(
                        attribute=alias,
                        operation=PatchOperation.UPDATE,
                        old_value=old_value,
                        new_value=new_value,
                    )
                )

        return PatchPayload(data=data)
