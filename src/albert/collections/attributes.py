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
from albert.exceptions import NotFoundError
from albert.resources.attributes import (
    Attribute,
    AttributeCategory,
    AttributeScope,
    AttributeSearchItem,
    AttributeValue,
    AttributeValuesResponse,
    AttributeValuesResponseItem,
)
from albert.resources.parameter_groups import DataType
from albert.utils._patch import generate_enum_patches


class AttributeCollection(BaseCollection):
    """Manage inventory reference Attributes in the Albert platform (🧪 Beta).

    An Attribute is a centralized, reusable *inventory reference property*
    template (e.g. "Viscosity @ 25°C"): it names what to track, which
    [`DataColumn`][albert.resources.data_columns.DataColumn] it maps to, optional
    parameter setpoints (e.g. Temperature = 25°C), an optional unit, and typed
    validation. *Reference values* are the actual measured or assigned values for
    that attribute on a specific inventory item or lot.

    The API separates **definition** (create
    [`Attribute`][albert.resources.attributes.Attribute] definitions) from **assignment**
    (store values on a parent with
    [`add_values`][albert.collections.attributes.AttributeCollection.add_values]).
    Inventory-level values are the source of truth for worksheet lookup columns;
    worksheet cells may override locally for what-if analysis without writing back
    to inventory.

    This replaces the deprecated per-item Inventory Specs API
    ([`get_specs`][albert.collections.inventory.InventoryCollection.get_specs],
    [`add_specs`][albert.collections.inventory.InventoryCollection.add_specs]).

    Attributes are identified by Attribute ID (format ``ATR...``, e.g.
    ``"ATR469"``). Reference values are keyed by ``parent_id``: inventory items
    (``INV...``), lots (``LOT...``), or other parent types as the platform expands.

    This collection is accessed as ``client.attributes``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert
        from albert.resources.attributes import (
            Attribute,
            AttributeCategory,
            AttributeValue,
            ValidationItem,
        )
        from albert.resources.parameter_groups import DataType, Operator

        client = Albert()
        viscosity = client.attributes.create(
            attribute=Attribute(
                datacolumn_id="DAC123",
                category=AttributeCategory.PROPERTY,
                reference_name="Viscosity @ 25°C",
                validation=[
                    ValidationItem(
                        datatype=DataType.NUMBER,
                        min=0.0,
                        max=500.0,
                        operator=Operator.BETWEEN,
                    )
                ],
            )
        )
        client.attributes.add_values(
            parent_id="INVA123",
            values=[AttributeValue(attributeId=viscosity.id, referenceValue=45.2)],
        )
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for attribute requests.

    Methods
    -------
    get_all(...) -> Iterator[Attribute]
        Get all attributes, with optional filters.
    get_by_id(id) -> Attribute
        Get a single attribute by its ID.
    get_by_ids(ids) -> list[Attribute]
        Get multiple attributes by their IDs.
    create(attribute) -> Attribute
        Create a new attribute.
    update(attribute) -> Attribute
        Update an existing attribute.
    delete(id) -> None
        Delete an attribute by its ID.
    search(...) -> Iterator[AttributeSearchItem]
        Search for attributes matching the given filters.
    add_values(parent_id, values) -> AttributeValuesResponse
        Add or update reference values for a parent entity.
    get_values(parent_id, scope, start_key, max_items) -> Iterator[AttributeValuesResponse]
        Get reference values for a parent entity.
    get_by_parent_ids(parent_ids, max_items) -> list[AttributeValuesResponse]
        Get reference values for multiple parent entities.
    delete_values(parent_id, attribute_ids, scope) -> None
        Delete specific reference values from a parent entity.
    clear_values(parent_id, scope) -> None
        Remove all reference values from a parent entity.
    """

    _updatable_attributes = {"reference_name", "parameters", "validation"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize the AttributeCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
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
        """Get all attribute definitions, with optional filters.

        Lists reusable inventory reference property templates (e.g. "Viscosity @
        25°C") that can be assigned to inventory items and lots. Use
        [`search`][albert.collections.attributes.AttributeCollection.search] for
        full-text and field filters across the catalogue.

        Parameters
        ----------
        category : AttributeCategory, optional
            Filter attributes by category (currently ``Property``).
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
        """Get a single attribute definition by its ID.

        Returns the full template: linked data column, parameter setpoints, unit,
        and validation rules used when assigning reference values.

        Parameters
        ----------
        id : str
            The attribute ID (format ``ATR...``).

        Returns
        -------
        Attribute
            The fully populated attribute.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Attribute(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[AttributeId]) -> list[Attribute]:
        """Get multiple attributes by their IDs.

        Parameters
        ----------
        ids : list[str]
            A list of attribute IDs.

        Returns
        -------
        list[Attribute]
            The fully populated attributes.
        """
        response = self.session.get(f"{self.base_path}/ids", params={"id": ids})
        data = response.json()
        items = data.get("Items") or data.get("items") or []
        return [Attribute(**item) for item in items]

    @validate_call
    def create(self, *, attribute: Attribute) -> Attribute:
        """Create a new inventory reference attribute definition.

        Define the property template once in the attribute catalogue, then assign values to
        inventory items or lots with [`add_values`][albert.collections.attributes.AttributeCollection.add_values].
        Uniqueness is enforced on name and on the data column, unit, and parameter
        setpoint combination.

        Parameters
        ----------
        attribute : Attribute
            The attribute to create.

        Returns
        -------
        Attribute
            The fully populated attribute.
        """
        payload = attribute.model_dump(
            by_alias=True, exclude_unset=True, mode="json", exclude={"id"}
        )
        response = self.session.post(self.base_path, json=payload)
        return Attribute(**response.json())

    @validate_call
    def update(self, *, attribute: Attribute) -> Attribute:
        """Update an existing attribute definition.

        Changes apply to the attribute definition. Inventory items that already
        store reference values keep their assignments; worksheet cells that
        previously imported a value are not updated automatically.

        Parameters
        ----------
        attribute : Attribute
            The updated Attribute object. Must have an ID set.

        Returns
        -------
        Attribute
            The fully populated attribute.

        Notes
        -----
        The following fields can be updated: ``reference_name``, ``parameters``,
        ``validation``. ``reference_name`` must remain unique across definitions.
        ``unit_id`` can only be set once (when no unit is currently assigned); it
        cannot be changed afterwards.
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
        """Delete an attribute definition by its ID.

        Removes the template from the attribute catalogue and its inventory-level
        reference values. Worksheet cells that already imported a value retain
        their local copy.

        Parameters
        ----------
        id : str
            The attribute ID (format ``ATR...``).

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
        """Search the central attribute catalogue.

        Full-text and field filters help locate reusable definitions when wiring
        worksheet lookup columns or assigning values on inventory details.

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
        """Add or update reference values on a parent entity.

        Upserts values for the given attributes on ``parent_id`` (inventory item,
        lot, etc.). Values must match each attribute's datatype. Inventory-level
        values feed worksheet lookups; each inventory item holds its own values.
        Attributes not listed in ``values`` are left unchanged.

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
        with suppress(NotFoundError):
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
        """Get reference values for a parent entity.

        Returns one [`AttributeValuesResponse`][albert.resources.attributes.AttributeValuesResponse]
        per entity when ``scope`` includes child lots. Inventory item values are
        the canonical source for worksheet reference columns.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity.
        scope : AttributeScope, optional
            Defines which entities to fetch values for.
            ``SELF`` (default): the parent entity only.
            ``LOT``: lot entities under the parent (inventory parents only).
            ``ALL``: parent and all child entities.
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
    def get_by_parent_ids(
        self,
        *,
        parent_ids: list[str],
        max_items: int | None = None,
    ) -> list[AttributeValuesResponse]:
        """Get reference values for multiple parent entities.

        Bulk read across inventory items (replaces deprecated
        [`get_specs`][albert.collections.inventory.InventoryCollection.get_specs]).

        Parameters
        ----------
        parent_ids : list[str]
            The IDs of the parent entities to fetch values for.
        max_items : int | None, optional
            Maximum total number of attribute value items to return across all
            parents. When None (default), all pages are fetched for every parent.

        Returns
        -------
        list[AttributeValuesResponse]
            Attribute values for each parent entity that has values set.
        """
        pending: list[dict] = [{"parentId": pid} for pid in parent_ids]
        accumulated: dict[str, list[AttributeValuesResponseItem]] = {}
        total = 0

        while pending:
            response = self.session.post(f"{self.base_path}/values", json=pending)
            next_pending: list[dict] = []
            for item in response.json().get("items") or []:
                parsed = AttributeValuesResponse.model_validate(item)
                accumulated.setdefault(parsed.parent_id, []).extend(parsed.attributes)
                total += len(parsed.attributes)
                if last_key := item.get("lastKey"):
                    next_pending.append({"parentId": parsed.parent_id, "startKey": last_key})
            pending = next_pending
            if max_items is not None and total >= max_items:
                break

        return [
            AttributeValuesResponse.model_validate({"parentId": pid, "attributes": attrs})
            for pid, attrs in accumulated.items()
        ]

    @validate_call
    def delete_values(
        self,
        *,
        parent_id: str,
        attribute_ids: list[AttributeId],
        scope: AttributeScope | None = None,
    ) -> None:
        """Delete specific reference values from a parent entity.

        Removes assignments for the given attributes on ``parent_id`` without
        deleting the attribute definitions themselves. Use ``scope`` to target lot-level
        values under an inventory parent.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity (inventory item ``INV...`` or lot ``LOT...``).
        attribute_ids : list[str]
            The attribute IDs whose values should be removed.
        scope : AttributeScope, optional
            Scope of deletion. Defaults to ``SELF`` (only ``parent_id``).

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

        Clears every assignment on ``parent_id`` while leaving attribute
        definitions in the attribute catalogue. Use ``scope`` to clear lot values
        under an inventory item.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity (inventory item ``INV...`` or lot ``LOT...``).
        scope : AttributeScope, optional
            Scope of deletion. Defaults to ``SELF`` (only ``parent_id``).

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
