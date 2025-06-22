from __future__ import annotations

from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.exceptions import AlbertHTTPError
from albert.resources.common.models import OrderBy
from albert.resources.common.patch import PatchOperation
from albert.resources.parameter_groups import (
    EnumValidationValue,
    ParameterGroup,
    ParameterGroupSearchItem,
    PGPatchDatum,
    PGPatchPayload,
    PGType,
)
from albert.utils._patch_utils import _split_patch_types_for_params_and_data_cols


class ParameterGroupCollection(BaseCollection):
    """ParameterGroupCollection is a collection class for managing ParameterGroup entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "description", "metadata"}
    # To do: Add the rest of the allowed attributes

    def __init__(self, *, session: AlbertSession):
        """A collection for interacting with Albert parameter groups.

        Parameters
        ----------
        session : AlbertSession
            The Albert session to use for making requests.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterGroupCollection._api_version}/parametergroups"

    def _handle_special_update_parameters(
        self,
        *,
        existing: ParameterGroup,
        updated: ParameterGroup,
    ) -> tuple[list[dict], dict]:
        """Handle special update parameters.

        Parameters
        ----------
        existing : ParameterGroup
            The existing parameter group.
        updated : ParameterGroup
            The updated parameter group.

        Returns
        -------
        tuple[list[dict], dict, list[dict]]
            The payload for the special update parameters.
        """
        _special_update_attributes = {"parameters"}
        new_patches = []
        enum_patches = {}
        new_param_patches = []
        for attr in _special_update_attributes:
            if attr == "parameters":
                # Handle the special case of updating parameters
                existing_params = [x.sequence for x in existing.parameters]
                updated_params = [x.sequence for x in updated.parameters]

                to_add = [x for x in updated.parameters if x.sequence not in existing_params]
                to_delete = set(existing_params) - set(updated_params)
                to_update = set(existing_params) & set(updated_params)
                # Add new parameters
                new_param_patches = [
                    x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in to_add
                ]
                # Delete removed parameters
                for sequence in to_delete:
                    if sequence not in enum_patches:
                        enum_patches[sequence] = []
                    new_patches.append(
                        PGPatchDatum(operation="delete", attribute="parameters", oldValue=sequence)
                    )
                # Update existing parameters
                for sequence in to_update:
                    if sequence not in enum_patches:
                        enum_patches[sequence] = []
                    existing_param_value = [
                        x for x in existing.parameters if x.sequence == sequence
                    ][0]
                    updated_param_value = [
                        x for x in updated.parameters if x.sequence == sequence
                    ][0]

                    if (
                        existing_param_value.validation != updated_param_value.validation
                        and updated_param_value.validation is not None
                        and isinstance(updated_param_value.validation[0].value, list)
                    ):
                        existing_enums = (
                            []
                            if existing_param_value.validation is None
                            or not isinstance(existing_param_value.validation[0].value, list)
                            else existing_param_value.validation[0].value
                        )
                        updated_enums = (
                            []
                            if updated_param_value.validation is None
                            else updated_param_value.validation[0].value
                        )

                        existing_enum_names = [
                            x.text for x in existing_enums if isinstance(x, EnumValidationValue)
                        ]
                        updated_enum_names = [
                            x.text for x in updated_enums if isinstance(x, EnumValidationValue)
                        ]
                        new_enums_names = set(updated_enum_names) - set(existing_enum_names)
                        deleted_enum_names = set(existing_enum_names) - set(updated_enum_names)
                        for new_enum_name in new_enums_names:
                            enum_patches[sequence].append(
                                {
                                    "operation": "add",
                                    "text": new_enum_name,
                                }
                            )
                        for deleted_enum in deleted_enum_names:
                            deleted_enum = [x for x in existing_enums if x.text == deleted_enum][0]
                            enum_patches[sequence].append(
                                {
                                    "operation": "delete",
                                    "id": deleted_enum.id,
                                }
                            )

                    elif existing_param_value.validation != updated_param_value.validation:
                        new_patches.append(
                            PGPatchDatum(
                                operation=PatchOperation.UPDATE,
                                attribute="validation",
                                newValue=[
                                    x.model_dump(mode="json", by_alias=True, exclude_none=True)
                                    for x in updated_param_value.validation
                                ]
                                if updated_param_value.validation is not None
                                else [],
                                rowId=existing_param_value.sequence,
                            )
                        )
                    if existing_param_value.unit != updated_param_value.unit:
                        if existing_param_value.unit is None:
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.ADD,
                                    attribute="unitId",
                                    newValue=updated_param_value.unit.id,
                                    rowId=existing_param_value.sequence,
                                )
                            )
                        elif updated_param_value.unit is None:
                            # For some reason, our backend blocks this, but I think it's best to let the backend error raise to make this clear to the user
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.DELETE,
                                    attribute="unitId",
                                    oldValue=existing_param_value.unit.id,
                                    rowId=existing_param_value.sequence,
                                )
                            )
                        elif existing_param_value.unit.id != updated_param_value.unit.id:
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.UPDATE,
                                    attribute="unitId",
                                    oldValue=existing_param_value.unit.id,
                                    newValue=updated_param_value.unit.id,
                                    rowId=existing_param_value.sequence,
                                )
                            )
                    if existing_param_value.value != updated_param_value.value:
                        if existing_param_value.value is None:
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.ADD,
                                    attribute="value",
                                    newValue=updated_param_value.value,
                                    rowId=updated_param_value.sequence,
                                )
                            )

                        elif updated_param_value.value is None:
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.DELETE,
                                    attribute="value",
                                    oldValue=existing_param_value.value,
                                    rowId=existing_param_value.sequence,
                                )
                            )
                        else:
                            new_patches.append(
                                PGPatchDatum(
                                    operation=PatchOperation.UPDATE,
                                    attribute="value",
                                    oldValue=existing_param_value.value,
                                    newValue=updated_param_value.value,
                                    rowId=existing_param_value.sequence,
                                )
                            )
        return (new_patches, enum_patches, new_param_patches)

    def get_by_id(self, *, id: str) -> ParameterGroup:
        """Get a parameter group by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter group to retrieve.

        Returns
        -------
        ParameterGroup
            The parameter group with the given ID.
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return ParameterGroup(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> ParameterGroup:
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            ParameterGroup(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def search(
        self,
        *,
        text: str | None = None,
        types: PGType | list[PGType] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 25,
        offset: int | None = None,
    ) -> Iterator[ParameterGroupSearchItem]:
        """Search for Parameter Groups matching the given criteria.

        Parameters
        ----------
        text : str | None, optional
            Text to search for, by default None
        types : PGType | list[PGType] | None, optional
            Filer the returned Parameter Groups by Type, by default None
        order_by : OrderBy, optional
            The order in which to return results, by default OrderBy.DESCENDING

        Yields
        ------
        Iterator[ParameterGroup]
            An iterator of Parameter Groups matching the given criteria.
        """

        params = {
            "limit": limit,
            "offset": offset,
            "order": order_by.value,
            "text": text,
            "types": [types] if isinstance(types, PGType) else types,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=lambda items: [ParameterGroupSearchItem(**item) for item in items],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
        types: PGType | list[PGType] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 25,
        offset: int | None = None,
    ) -> Iterator[ParameterGroup]:
        """Search and hydrate all Parameter Groups matching the given criteria.

        Parameters
        ----------
        text : str | None, optional
            Text to search for, by default None.
        types : PGType | list[PGType] | None, optional
            Filter the returned Parameter Groups by Type, by default None.
        order_by : OrderBy, optional
            The order in which to return results, by default OrderBy.DESCENDING.
        limit : int, optional
            Page size for each search request, by default 25.
        offset : int | None, optional
            Offset to start from, by default None.

        Yields
        ------
        Iterator[ParameterGroup]
            An iterator of fully hydrated Parameter Groups.
        """
        for item in self.search(
            text=text,
            types=types,
            order_by=order_by,
            limit=limit,
            offset=offset,
        ):
            try:
                # Currently, the API is not returning Metadata, Tags, Documents, and ACL for the get_by_ids endpoint, so we need to fetch individually until that is fixed
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:  # pragma: no cover
                logger.warning(f"Error fetching parameter group {item.id}: {e}")

    def delete(self, *, id: str) -> None:
        """Delete a parameter group by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter group to delete
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def create(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Create a new parameter group.

        Parameters
        ----------
        parameter_group : ParameterGroup
            The parameter group to create.

        Returns
        -------
        ParameterGroup
            The created parameter group.
        """

        response = self.session.post(
            self.base_path,
            json=parameter_group.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ParameterGroup(**response.json())

    def get_by_name(self, *, name: str) -> ParameterGroup | None:
        """Get a parameter group by its name.

        Parameters
        ----------
        name : str
            The name of the parameter group to retrieve.

        Returns
        -------
        ParameterGroup | None
            The parameter group with the given name, or None if not found.
        """
        matches = self.get_all(text=name)
        # TODO: optimize with explicit hydrate() after self.search()
        for m in matches:
            if m.name.lower() == name.lower():
                return m
        return None

    def update(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Update a parameter group.

        Parameters
        ----------
        parameter_group : ParameterGroup
            The updated ParameterGroup. The ParameterGroup must have an ID.

        Returns
        -------
        ParameterGroup
            The updated ParameterGroup as returned by the server.
        """
        existing = self.get_by_id(id=parameter_group.id)
        path = f"{self.base_path}/{existing.id}"

        base_payload, list_metadata_updates = self._generate_patch_payload(
            existing=existing,
            updated=parameter_group,
        )

        # Handle special update parameters
        special_patches, special_enum_patches, new_param_patches = (
            _split_patch_types_for_params_and_data_cols(existing=existing, updated=parameter_group)
        )

        patch_operations = list(base_payload.data) + special_patches

        for datum in patch_operations:
            patch_payload = PGPatchPayload(data=[datum])
            self.session.patch(
                path, json=patch_payload.model_dump(mode="json", by_alias=True, exclude_none=True)
            )

        # For metadata list field updates, we clear, then update
        # since duplicate attribute values are not allowed in single patch request.
        for attribute, values in list_metadata_updates.items():
            clear_payload = PGPatchPayload(
                data=[PGPatchDatum(operation="update", attribute=attribute, newValue=None)]
            )
            self.session.patch(
                path, json=clear_payload.model_dump(mode="json", by_alias=True, exclude_none=True)
            )
            if values:
                update_payload = PGPatchPayload(
                    data=[PGPatchDatum(operation="update", attribute=attribute, newValue=values)]
                )
                self.session.patch(
                    path,
                    json=update_payload.model_dump(mode="json", by_alias=True, exclude_none=True),
                )

        # handle adding new parameters
        if len(new_param_patches) > 0:
            self.session.put(
                f"{self.base_path}/{existing.id}/parameters",
                json={"Parameters": new_param_patches},
            )
        # Handle special enum update parameters
        for sequence, enum_patches in special_enum_patches.items():
            if len(enum_patches) == 0:
                continue
            enum_path = f"{self.base_path}/{existing.id}/parameters/{sequence}/enums"
            self.session.put(enum_path, json=enum_patches)
        return self.get_by_id(id=parameter_group.id)

    def _is_metadata_item_list(
        self,
        *,
        existing_object: ParameterGroup,
        updated_object: ParameterGroup,
        metadata_field: str,
    ) -> bool:
        """Return True if the metadata field is a list type on either object."""

        if not metadata_field.startswith("Metadata."):
            return False

        metadata_field = metadata_field.split(".")[1]

        if existing_object.metadata is None:
            existing_object.metadata = {}
        if updated_object.metadata is None:
            updated_object.metadata = {}

        existing = existing_object.metadata.get(metadata_field, None)
        updated = updated_object.metadata.get(metadata_field, None)

        return isinstance(existing, list) or isinstance(updated, list)

    def _generate_patch_payload(
        self,
        *,
        existing: ParameterGroup,
        updated: ParameterGroup,
    ) -> tuple[PGPatchPayload, dict[str, list[str]]]:
        """Generate a patch payload and capture metadata list updates."""

        base_payload = super()._generate_patch_payload(
            existing=existing,
            updated=updated,
        )

        new_data: list[PGPatchDatum] = []
        list_metadata_updates: dict[str, list[str]] = {}

        for datum in base_payload.data:
            if self._is_metadata_item_list(
                existing_object=existing,
                updated_object=updated,
                metadata_field=datum.attribute,
            ):
                key = datum.attribute.split(".", 1)[1]
                updated_list = updated.metadata.get(key) or []
                list_values: list[str] = [
                    item.id if hasattr(item, "id") else item for item in updated_list
                ]

                list_metadata_updates[datum.attribute] = list_values
                continue

            new_data.append(
                PGPatchDatum(
                    operation=datum.operation,
                    attribute=datum.attribute,
                    newValue=datum.new_value,
                    oldValue=datum.old_value,
                )
            )

        return PGPatchPayload(data=new_data), list_metadata_updates
