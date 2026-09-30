from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import CustomFieldId
from albert.resources.custom_fields import (
    CustomField,
    EntityCategory,
    FieldType,
    SearchableCustomField,
    ServiceType,
)
from albert.utils.custom_fields import _generate_custom_field_patch_payload


class CustomFieldCollection(BaseCollection):
    """Manage Custom Fields in the Albert platform.

    A Custom Field defines an allowed metadata field on an Albert entity. The
    ``metadata`` dicts on entities such as Projects, Inventory Items, Users, Tasks,
    and Lots may only use fields that have been defined here; a Custom Field is
    the schema that gives a metadata key its name, type, and validation rules.

    The field's [`FieldType`][albert.resources.custom_fields.FieldType] determines the
    shape of the stored value (e.g. ``string``, ``number``, ``list``). When the
    type is ``list``, the [`FieldCategory`][albert.resources.custom_fields.FieldCategory]
    determines who may add new allowed items to that list:

    - ``FieldCategory.USER_DEFINED``: general users can add items.
    - ``FieldCategory.BUSINESS_DEFINED``: only admins can add items.

    Creating a ``list`` custom field establishes a new list (identified by a
    ``list_type``, typically the field's name) for options to be added to. Those
    options are [`ListItem`][albert.resources.lists.ListItem] records managed through
    [`ListsCollection`][albert.collections.lists.ListsCollection] (``client.lists``); add
    each option with its ``list_type`` set to this field.

    Custom Field IDs use the ``CTF`` prefix. This is configuration/schema-level
    data.

    This collection is accessed as ``client.custom_fields``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.custom_fields import (
            CustomField,
            FieldCategory,
            FieldType,
            ServiceType,
        )
        client = Albert()
        # A business-defined single-select list field on Projects
        stage_gate_field = CustomField(
            name="stage_gate_status",
            display_name="Stage Gate",
            field_type=FieldType.LIST,
            service=ServiceType.PROJECTS,
            min=1,
            max=1,
            category=FieldCategory.BUSINESS_DEFINED,
        )
        # A free-text field on Projects
        justification_field = CustomField(
            name="justification",
            display_name="Project Justification",
            field_type=FieldType.STRING,
            service=ServiceType.PROJECTS,
        )
        client.custom_fields.create(custom_field=stage_gate_field)
        client.custom_fields.create(custom_field=justification_field)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for custom field requests.

    Methods
    -------
    create(custom_field) -> CustomField
        Create a new custom field.
    get_by_id(id) -> CustomField
        Get a single custom field by its ID.
    get_by_name(name, service=None) -> CustomField | None
        Get a custom field by its name.
    get_all(...) -> Iterator[CustomField]
        Iterate over custom fields matching optional filters.
    get_searchable_fields(entity) -> dict[str, SearchableCustomField]
        Return the searchable custom fields configured for an entity/service.
    update(custom_field) -> CustomField
        Update an existing custom field.
    delete(id) -> None
        Delete a custom field by its ID.
    """

    _updatable_attributes = {
        "display_name",
        "searchable",
        "hidden",
        "lookup_column",
        "lookup_row",
        "min",
        "max",
        "entity_categories",
        "ui_components",
        "required",
        "multiselect",
        "pattern",
        "default",
        "custom_entity_categories",
        "editable",
    }
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a CustomFieldCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CustomFieldCollection._api_version}/customfields"

    @validate_call
    def get_by_id(self, *, id: CustomFieldId) -> CustomField:
        """Get a single custom field by its ID.

        !!! example
            ```python
            cf = client.custom_fields.get_by_id(id="CTF1")
            cf.name
            # 'stage_gate_status'
            ```

        Parameters
        ----------
        id : CustomFieldId
            The Custom Field ID (format ``CTF...``).

        Returns
        -------
        CustomField
            The fully populated custom field.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return CustomField(**response.json())

    def get_by_name(self, *, name: str, service: ServiceType | None = None) -> CustomField | None:
        """Get a custom field by its name.

        Matching is case-insensitive. Pass ``service`` to disambiguate when the
        same field name is used across different services.

        !!! example
            ```python
            from albert.resources.custom_fields import ServiceType
            cf = client.custom_fields.get_by_name(
                name="stage_gate_status",
                service=ServiceType.PROJECTS,
            )
            cf.id if cf else "not found"
            # 'CTF1'
            ```

        Parameters
        ----------
        name : str
            The name of the custom field (the ``name`` attribute, not the display
            name).
        service : ServiceType, optional
            The service the field relates to. Defaults to all services.

        Returns
        -------
        CustomField or None
            The matching custom field, or None if not found.
        """
        for custom_field in self.get_all(name=name, service=service):
            if custom_field.name.lower() == name.lower():
                return custom_field
        return None

    def get_all(
        self,
        *,
        name: str | None = None,
        type: FieldType | None = None,
        service: ServiceType | None = None,
        lookup_column: bool | None = None,
        lookup_row: bool | None = None,
        entity_category: EntityCategory | None = None,
        custom_entity_category: str | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[CustomField]:
        """Iterate over custom fields matching the given filters.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand.

        !!! example
            ```python
            from albert.resources.custom_fields import ServiceType
            for cf in client.custom_fields.get_all(
                service=ServiceType.PROJECTS,
                max_items=50,
            ):
                print(cf.id, cf.name)
            ```

        Parameters
        ----------
        name : str, optional
            Filter by field name.
        type : FieldType, optional
            Filter by field type (e.g. ``string``, ``number``, ``list``).
        service : ServiceType, optional
            Filter by the service the field belongs to. If none, none will be returned. So, for best expected results, pass a service.
        lookup_column : bool, optional
            Filter to fields that are (or are not) lookup columns.
        lookup_row : bool, optional
            Filter to fields that are (or are not) lookup rows.
        entity_category : EntityCategory, optional
            Filter by supported entity category for the field.
        custom_entity_category : str, optional
            Filter by custom entity category configured for the field.
        start_key : str, optional
            Provide the ``lastKey`` from a previous request to resume pagination.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[CustomField]
            A lazily paginated iterator of matching custom fields.
        """
        params = {
            "name": name,
            "type": type,
            "service": service,
            "lookupColumn": lookup_column,
            "lookupRow": lookup_row,
            "entityCategory": entity_category,
            "customEntityCategory": custom_entity_category,
            "startKey": start_key,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [CustomField(**item) for item in items],
        )

    @validate_call
    def get_searchable_fields(self, *, entity: ServiceType) -> dict[str, SearchableCustomField]:
        """Return the custom fields configured as searchable for an entity.

        Only ``string`` and ``list`` fields can be made searchable. Use this to
        discover which metadata paths on an entity can be queried in search.

        !!! example
            ```python
            from albert.resources.custom_fields import ServiceType
            fields = client.custom_fields.get_searchable_fields(
                entity=ServiceType.PROJECTS
            )
            list(fields)
            # ['Metadata.stage_gate_status', ...]
            ```

        Parameters
        ----------
        entity : ServiceType
            The entity/service to fetch searchable fields for.

        Returns
        -------
        dict[str, SearchableCustomField]
            Mapping of metadata paths to their searchable field descriptors.
        """

        response = self.session.get(
            f"{self.base_path}/searchable",
            params={"entity": entity},
        )
        response = response.json()
        return {key: SearchableCustomField(**value) for key, value in response.items()}

    def create(self, *, custom_field: CustomField) -> CustomField:
        """Create a new custom field.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.custom_fields import (
                CustomField,
                FieldType,
                ServiceType,
            )
            client = Albert()
            field = CustomField(
                name="justification",
                display_name="Project Justification",
                field_type=FieldType.STRING,
                service=ServiceType.PROJECTS,
            )
            created = client.custom_fields.create(custom_field=field)
            created.id
            # 'CTF1'
            ```

        Parameters
        ----------
        custom_field : CustomField
            The custom field to create. ``name``, ``display_name``,
            ``field_type``, and ``service`` are required; ``list`` fields also
            require a ``category``.

        Returns
        -------
        CustomField
            The newly created custom field, populated with its assigned Custom
            Field ID.
        """
        response = self.session.post(
            self.base_path,
            json=custom_field.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return CustomField(**response.json())

    def update(self, *, custom_field: CustomField) -> CustomField:
        """Update an existing custom field.

        Fetch the field (e.g. with [`get_by_id`][albert.collections.custom_fields.CustomFieldCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Only the fields listed in Notes
        are applied; changes to other fields are ignored.

        !!! example
            ```python
            cf = client.custom_fields.get_by_id(id="CTF1")
            cf.display_name = "Updated display name"
            updated = client.custom_fields.update(custom_field=cf)
            updated.display_name
            # 'Updated display name'
            ```

        Parameters
        ----------
        custom_field : CustomField
            The custom field to update. Its ``id`` must be set and match the field
            being updated.

        Returns
        -------
        CustomField
            The updated custom field as registered in Albert.

        Notes
        -----
        The following fields can be updated: ``custom_entity_categories``,
        ``default``, ``display_name``, ``editable``, ``entity_categories``,
        ``hidden``, ``lookup_column``, ``lookup_row``, ``max``, ``min``,
        ``multiselect``, ``pattern``, ``required``, ``searchable``,
        ``ui_components``.
        """
        # fetch current object state
        current_object = self.get_by_id(id=custom_field.id)

        # generate the patch payload
        payload = _generate_custom_field_patch_payload(
            existing=current_object,
            updated=custom_field,
            updatable_attributes=self._updatable_attributes,
        )

        # run patch
        url = f"{self.base_path}/{custom_field.id}"

        self.session.patch(
            url,
            json=payload.model_dump(
                mode="json", by_alias=True, exclude_unset=False, exclude_none=True
            ),
        )
        updated_ctf = self.get_by_id(id=custom_field.id)
        return updated_ctf

    @validate_call
    def delete(self, *, id: CustomFieldId) -> None:
        """Delete a custom field by its ID.

        !!! example
            ```python
            client.custom_fields.delete(id="CTF1")
            ```

        Parameters
        ----------
        id : CustomFieldId
            The Custom Field ID to delete (format ``CTF...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
