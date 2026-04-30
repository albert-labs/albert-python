from collections.abc import Iterator
from contextlib import suppress
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import AttributeId, DataColumnId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.exceptions import AlbertException
from albert.resources.attributes import (
    Attribute,
    AttributeCategory,
    AttributeScope,
    AttributeSearchItem,
    AttributeValue,
    AttributeValuesResponse,
)
from albert.resources.parameter_groups import DataType
from albert.utils._patch import generate_enum_patches


class AttributeCollection(BaseCollection):
    """AttributeCollection manages Attribute entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for attribute API requests.

    Methods
    -------
    get_all(category, start_key, max_items) -> Iterator[Attribute]
        Lists all attributes with optional filters.
    get_by_id(id) -> Attribute
        Retrieves an attribute by its ID.
    get_by_ids(ids) -> list[Attribute]
        Retrieves multiple attributes by their IDs.
    create(attribute) -> Attribute
        Creates a new attribute.
    update(attribute) -> Attribute
        Updates an existing attribute.
    delete(id) -> None
        Deletes an attribute by its ID.
    search(...) -> Iterator[AttributeSearchItem]
        Searches for attributes.
    add_values(parent_id, values) -> AttributeValuesResponse
        Adds or updates reference values for a parent entity.
    get_values(parent_id, scope, start_key, max_items) -> Iterator[AttributeValuesResponse]
        Retrieves reference values for a parent entity.
    get_bulk_values(parent_ids) -> list[AttributeValuesResponse]
        Retrieves reference values for multiple parent entities.
    delete_values(parent_id, attribute_ids, scope) -> None
        Deletes specific reference values from a parent entity.
    clear_values(parent_id, scope) -> None
        Removes all reference values from a parent entity.
    """

    _updatable_attributes = {"reference_name", "parameters", "validation"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize the AttributeCollection.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/attributes"

    @validate_call
    def get_all(
        self,
        *,
        category: AttributeCategory | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Attribute]:
        """List all attributes with optional filters.

        Parameters
        ----------
        category : AttributeCategory, optional
            Filter attributes by category.
        start_key : str, optional
            Pagination start key from a previous request.
        max_items : int, optional
            Maximum number of items to return.

        Returns
        -------
        Iterator[Attribute]
            An iterator over Attribute entities.
        """
        params: dict[str, Any] = {}
        if category is not None:
            params["category"] = category.value
        if start_key is not None:
            params["startKey"] = start_key

        yield from AlbertPaginator(
            path=self.base_path,
            mode=PaginationMode.KEY,
            session=self.session,
            deserialize=lambda items: [Attribute(**item) for item in items],
            params=params,
            max_items=max_items,
        )

    @validate_call
    def get_by_id(self, *, id: AttributeId) -> Attribute:
        """Retrieve an attribute by its ID.

        Parameters
        ----------
        id : str
            The attribute ID.

        Returns
        -------
        Attribute
            The matching Attribute.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Attribute(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[AttributeId]) -> list[Attribute]:
        """Retrieve multiple attributes by their IDs.

        Parameters
        ----------
        ids : list[str]
            A list of attribute IDs.

        Returns
        -------
        list[Attribute]
            The matching Attribute objects.
        """
        response = self.session.get(f"{self.base_path}/ids", params={"id": ids})
        data = response.json()
        items = data.get("Items") or data.get("items") or []
        return [Attribute(**item) for item in items]

    def create(self, *, attribute: Attribute) -> Attribute:
        """Create a new attribute.

        Parameters
        ----------
        attribute : Attribute
            The attribute to create.

        Returns
        -------
        Attribute
            The created Attribute.
        """
        payload = attribute.model_dump(
            by_alias=True, exclude_unset=True, mode="json", exclude={"id"}
        )
        response = self.session.post(self.base_path, json=payload)
        return Attribute(**response.json())

    def update(self, *, attribute: Attribute) -> Attribute:
        """Update an existing attribute.

        Enum value changes are handled transparently via a separate enums
        endpoint before applying any field-level patches.

        Parameters
        ----------
        attribute : Attribute
            The updated Attribute object. Must have an ID set.

        Returns
        -------
        Attribute
            The updated Attribute.
        """
        if attribute.id is None:
            raise ValueError("Attribute ID is required for update.")

        existing = self.get_by_id(id=attribute.id)

        enum_patches = self._generate_enum_patches(existing=existing, updated=attribute)
        if enum_patches:
            self.session.put(f"{self.base_path}/{attribute.id}/enums", json={"data": enum_patches})

        patch_payload = self._generate_attribute_patch_payload(
            existing=existing, updated=attribute, skip_validation=bool(enum_patches)
        )
        if len(patch_payload.data) > 0:
            self.session.patch(
                f"{self.base_path}/{attribute.id}",
                json=patch_payload.model_dump(by_alias=True, mode="json"),
            )

        return self.get_by_id(id=attribute.id)

    @validate_call
    def delete(self, *, id: AttributeId) -> None:
        """Delete an attribute by its ID.

        Parameters
        ----------
        id : str
            The attribute ID.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        datacolumn_id: list[DataColumnId] | None = None,
        datacolumn_name: list[str] | None = None,
        parameter: list[str] | None = None,
        unit: list[str] | None = None,
        data_type: list[DataType] | None = None,
        max_items: int | None = None,
    ) -> Iterator[AttributeSearchItem]:
        """Search for attributes with optional filters.

        Parameters
        ----------
        text : str, optional
            Full-text search term.
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort results by.
        datacolumn_id : list[str], optional
            Filter by data column IDs.
        datacolumn_name : list[str], optional
            Filter by data column names.
        parameter : list[str], optional
            Filter by parameter name(s) (e.g., ``["Temperature", "Pressure"]``).
        unit : list[str], optional
            Filter by unit name(s) (e.g., ``["cP", "MPa"]``).
        data_type : list[DataType], optional
            Filter by data type(s).
        max_items : int, optional
            Maximum number of items to return.

        Returns
        -------
        Iterator[AttributeSearchItem]
            An iterator over search results.
        """
        body: dict[str, Any] = {"order": order_by}
        if text is not None:
            body["text"] = text
        if sort_by is not None:
            body["sortBy"] = sort_by
        if datacolumn_id is not None:
            body["datacolumnId"] = datacolumn_id
        if datacolumn_name is not None:
            body["datacolumnName"] = datacolumn_name
        if parameter is not None:
            body["parameter"] = parameter
        if unit is not None:
            body["unit"] = unit
        if data_type is not None:
            body["dataType"] = data_type

        yield from AlbertPaginator(
            path=f"{self.base_path}/search",
            mode=PaginationMode.OFFSET,
            session=self.session,
            deserialize=lambda items: [AttributeSearchItem(**item) for item in items],
            method="POST",
            json=body,
            max_items=max_items,
        )

    # --- Attribute Values ---

    @validate_call
    def add_values(
        self,
        *,
        parent_id: str,
        values: list[AttributeValue],
    ) -> AttributeValuesResponse:
        """Add or update reference values for a parent entity.

        If a value already exists for any of the provided attributes it is
        replaced. Attributes not mentioned in ``values`` are left unchanged.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity (inventory item, lot, etc.).
        values : list[AttributeValue]
            The attribute values to add or update.

        Returns
        -------
        AttributeValuesResponse
            The saved attribute values with full attribute definitions.
        """
        attribute_ids = [v.attribute_id for v in values]
        with suppress(AlbertException):
            self.delete_values(parent_id=parent_id, attribute_ids=attribute_ids)
        payload = [v.model_dump(by_alias=True, mode="json", exclude_none=True) for v in values]
        response = self.session.put(f"{self.base_path}/values/{parent_id}", json=payload)
        return AttributeValuesResponse(**response.json())

    @validate_call
    def get_values(
        self,
        *,
        parent_id: str,
        scope: AttributeScope | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[AttributeValuesResponse]:
        """Retrieve reference values for a parent entity.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity.
        scope : AttributeScope, optional
            Defines which entities to fetch values for.
            ``SELF`` (default) — the parent entity only.
            ``LOT`` — lot entities under the parent (inventory parents only).
            ``ALL`` — parent and all child entities.
        start_key : str, optional
            Pagination start key from a previous request.
        max_items : int, optional
            Maximum number of items to return.

        Returns
        -------
        Iterator[AttributeValuesResponse]
            An iterator over attribute value responses, one per entity.
        """
        params: dict[str, Any] = {}
        if scope is not None:
            params["scope"] = scope.value
        if start_key is not None:
            params["startKey"] = start_key

        yield from AlbertPaginator(
            path=f"{self.base_path}/values/{parent_id}",
            mode=PaginationMode.KEY,
            session=self.session,
            deserialize=lambda items: [AttributeValuesResponse(**item) for item in items],
            params=params,
            max_items=max_items,
        )

    @validate_call
    def get_bulk_values(
        self,
        *,
        parent_ids: list[str],
    ) -> list[AttributeValuesResponse]:
        """Retrieve reference values for multiple parent entities in one call.

        Parameters
        ----------
        parent_ids : list[str]
            The IDs of the parent entities to fetch values for.

        Returns
        -------
        list[AttributeValuesResponse]
            Attribute values for each parent entity that has values set.
        """
        response = self.session.get(f"{self.base_path}/values", params={"parentId": parent_ids})
        data = response.json()
        items = data.get("Items") or data.get("items") or []
        return [AttributeValuesResponse(**item) for item in items]

    @validate_call
    def delete_values(
        self,
        *,
        parent_id: str,
        attribute_ids: list[AttributeId],
        scope: AttributeScope | None = None,
    ) -> None:
        """Delete specific reference values from a parent entity.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity.
        attribute_ids : list[str]
            The attribute IDs whose values should be removed.
        scope : AttributeScope, optional
            Scope of deletion. Defaults to ``SELF``.

        Returns
        -------
        None
        """
        params: dict[str, Any] = {"attributeId": attribute_ids}
        if scope is not None:
            params["scope"] = scope.value
        self.session.delete(f"{self.base_path}/values/{parent_id}", params=params)

    @validate_call
    def clear_values(
        self,
        *,
        parent_id: str,
        scope: AttributeScope | None = None,
    ) -> None:
        """Remove all reference values from a parent entity.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity.
        scope : AttributeScope, optional
            Scope of deletion. Defaults to ``SELF``.

        Returns
        -------
        None
        """
        params: dict[str, Any] = {}
        if scope is not None:
            params["scope"] = scope.value
        self.session.delete(f"{self.base_path}/values/{parent_id}", params=params)

    # --- Internal helpers ---

    def _generate_attribute_patch_payload(
        self, *, existing: Attribute, updated: Attribute, skip_validation: bool = False
    ) -> PatchPayload:
        data: list[PatchDatum] = []

        old_name = existing.reference_name
        new_name = updated.reference_name
        if new_name is not None and old_name != new_name:
            if old_name is None:
                data.append(
                    PatchDatum(
                        attribute="referenceName",
                        operation=PatchOperation.ADD,
                        new_value=new_name,
                    )
                )
            else:
                data.append(
                    PatchDatum(
                        attribute="referenceName",
                        operation=PatchOperation.UPDATE,
                        old_value=old_name,
                        new_value=new_name,
                    )
                )

        old_validation = existing.validation
        new_validation = updated.validation
        if not skip_validation and new_validation is not None and old_validation != new_validation:
            old_val_dump = (
                [v.model_dump(by_alias=True, mode="json") for v in old_validation]
                if old_validation
                else []
            )
            new_val_dump = [v.model_dump(by_alias=True, mode="json") for v in new_validation]
            if old_val_dump != new_val_dump:
                data.append(
                    PatchDatum(
                        attribute="validation",
                        operation=PatchOperation.UPDATE,
                        old_value=old_val_dump,
                        new_value=new_val_dump,
                    )
                )

        old_params = existing.parameters
        new_params = updated.parameters
        if new_params is not None:
            old_params_dump = self._dump_parameters(old_params)
            new_params_dump = self._dump_parameters(new_params)
            if old_params_dump != new_params_dump:
                data.append(
                    PatchDatum(
                        attribute="parameters",
                        operation=PatchOperation.UPDATE,
                        old_value=old_params_dump,
                        new_value=new_params_dump,
                    )
                )

        if updated.unit_id is not None and existing.unit is None:
            data.append(
                PatchDatum(
                    attribute="unitId",
                    operation=PatchOperation.ADD,
                    new_value=updated.unit_id,
                )
            )

        return PatchPayload(data=data)

    @staticmethod
    def _dump_parameters(params: list | None) -> list[dict[str, Any]]:
        if not params:
            return []
        return [p.model_dump(by_alias=True, mode="json", exclude_none=True) for p in params]

    @staticmethod
    def _generate_enum_patches(*, existing: Attribute, updated: Attribute) -> list[dict]:
        if not updated.validation or not existing.validation:
            return []

        updated_val = updated.validation[0]
        existing_val = existing.validation[0]

        if updated_val.datatype != DataType.ENUM or existing_val.datatype != DataType.ENUM:
            return []

        existing_enums = existing_val.value if isinstance(existing_val.value, list) else []
        updated_enums = updated_val.value if isinstance(updated_val.value, list) else []

        return generate_enum_patches(
            existing_enums=existing_enums,
            updated_enums=updated_enums,
        )
