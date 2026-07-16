from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import EntityTypeId
from albert.core.shared.models.patch import PatchDatum, PatchOperation
from albert.resources.entity_types import (
    EntityServiceType,
    EntityType,
    EntityTypeRule,
    EntityTypeSearchQueryStrings,
    EntityTypeStandardFieldRequired,
    EntityTypeStandardFieldVisibility,
)


class EntityTypeCollection(BaseCollection):
    """Manage Entity Types in the Albert platform.

    An Entity Type is a configurable definition that determines how a particular
    kind of entity (a Task, Inventory Item, Project, Data Template, Parameter
    Group, or Lot) looks and behaves. It groups together the custom category the
    entity falls under, which [`CustomField`][albert.resources.custom_fields.CustomField]
    values appear on it, how the standard Notes/Tags/Due Date fields are shown or
    required, and how searches for related entities are built.

    Entity Types come in two flavors (see
    [`EntityTypeType`][albert.resources.entity_types.EntityTypeType]): ``system`` types
    ship with the platform, while ``custom`` types are defined by an organization
    to model its own categories of work. Each type is scoped to a single service
    (see [`EntityServiceType`][albert.resources.entity_types.EntityServiceType]), such as
    ``tasks`` or ``inventories``.

    Entity Types are referenced by their Entity Type ID (format ``ETT...``).
    This is configuration/schema-level data; most users read Entity Types to
    understand how their platform is set up rather than creating them frequently.

    This collection is accessed as ``client.entity_types``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for entity type requests.

    Methods
    -------
    create(entity_type) -> EntityType
        Create a new entity type.
    get_by_id(id) -> EntityType
        Get a single entity type by its ID.
    get_all(...) -> Iterator[EntityType]
        Iterate over entity types, optionally filtered by service.
    update(entity_type) -> EntityType
        Update an existing entity type.
    delete(id) -> None
        Delete an entity type by its ID.
    get_rules(id) -> list[EntityTypeRule]
        Get the conditional field rules configured for an entity type.
    set_rules(id, rules) -> list[EntityTypeRule]
        Create or replace the conditional field rules for an entity type.
    delete_rules(id) -> None
        Remove the conditional field rules for an entity type.

    Examples
    --------
    ```python
    from albert import Albert
    from albert.resources.entity_types import EntityServiceType
    client = Albert()
    # List the entity types configured for Tasks
    for et in client.entity_types.get_all(service=EntityServiceType.TASKS):
        print(et.id, et.label)
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {
        "label",
        "template_based",
        "locked_template",
        "custom_fields",
        "standard_field_visibility",
        "standard_field_required",
        "search_query_string",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize an EntityTypeCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{EntityTypeCollection._api_version}/entitytypes"

    @validate_call
    def get_by_id(self, *, id: EntityTypeId) -> EntityType:
        """Get a single entity type by its ID.

        Parameters
        ----------
        id : EntityTypeId
            The Entity Type ID (format ``ETT...``).

        Returns
        -------
        EntityType
            The fully populated entity type.

        Examples
        --------
        ```python
        et = client.entity_types.get_by_id(id="ETT1")
        et.label
        # 'Formulation Task'
        ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return EntityType(**response.json())

    def create(self, *, entity_type: EntityType) -> EntityType:
        """Create a new entity type.

        Parameters
        ----------
        entity_type : EntityType
            The entity type to create. ``label`` and ``service`` are required, and
            ``category`` is required when the service is ``tasks`` or
            ``inventories``.

        Returns
        -------
        EntityType
            The newly created entity type, populated with its assigned Entity
            Type ID.

        Examples
        --------
        ```python
        from albert import Albert
        from albert.resources.entity_types import (
            EntityCategory,
            EntityServiceType,
            EntityType,
        )
        client = Albert()
        new_type = EntityType(
            label="Stability Task",
            service=EntityServiceType.TASKS,
            category=EntityCategory.PROPERTY,
        )
        created = client.entity_types.create(entity_type=new_type)
        created.id
        # 'ETT1'
        ```
        """
        response = self.session.post(
            self.base_path, json=entity_type.model_dump(by_alias=True, exclude_none=True)
        )
        return EntityType(**response.json())

    def update(self, *, entity_type: EntityType) -> EntityType:
        """Update an existing entity type.

        Fetch the entity type (e.g. with [`get_by_id`][albert.collections.entity_types.EntityTypeCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. Only the fields listed
        in Notes are applied; changes to other fields are ignored.

        Parameters
        ----------
        entity_type : EntityType
            The entity type to update. Must have a valid ``id``.

        Returns
        -------
        EntityType
            The updated entity type.

        Notes
        -----
        The following fields can be updated: ``custom_fields``, ``label``,
        ``locked_template``, ``search_query_string``, ``standard_field_required``,
        ``standard_field_visibility``, ``template_based``.

        Examples
        --------
        ```python
        et = client.entity_types.get_by_id(id="ETT1")
        et.label = "Updated label"
        updated = client.entity_types.update(entity_type=et)
        updated.label
        # 'Updated label'
        ```
        """
        current_entity_type = self.get_by_id(id=entity_type.id)
        patch = self._generate_patch_payload(
            existing=current_entity_type,
            updated=entity_type,
            generate_metadata_diff=False,
            stringify_values=False,
        )

        # Add special attribute updates to the patch
        special_patches = self._generate_special_attribute_patches(
            existing=current_entity_type, updated=entity_type
        )
        patch.data.extend(special_patches)

        self.session.patch(
            f"{self.base_path}/{entity_type.id}",
            json=patch.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return self.get_by_id(id=entity_type.id)

    def _generate_special_attribute_patches(
        self, *, existing: EntityType, updated: EntityType
    ) -> list[PatchDatum]:
        """Generate patches for special attributes that require custom handling.
        This method handles updates to:
        - Individual custom field properties (name, section, hidden, default)
        - Individual standard field visibility properties
        - Individual search query string properties (DAT, PRG)
        Parameters
        ----------
        existing : EntityType
            The current entity type state.
        updated : EntityType
            The desired entity type state.
        Returns
        -------
        list[PatchDatum]
            List of patch operations for special attributes.
        """
        patches = []

        def _nested_field_patch(attribute: str, old_value, new_value) -> PatchDatum:
            # A nested key that isn't set yet must be added; the backend rejects
            # an `update` on a path that does not already exist.
            if old_value is None:
                return PatchDatum(
                    operation=PatchOperation.ADD,
                    attribute=attribute,
                    new_value=new_value,
                )
            return PatchDatum(
                operation=PatchOperation.UPDATE,
                attribute=attribute,
                new_value=new_value,
                old_value=old_value,
            )

        if updated.custom_fields is not None and existing.custom_fields is not None:
            patches.append(
                PatchDatum(
                    operation=PatchOperation.UPDATE,
                    attribute="customFields",
                    new_value=[
                        x.model_dump(by_alias=True, exclude_none=True)
                        for x in updated.custom_fields
                    ],
                    old_value=[
                        x.model_dump(by_alias=True, exclude_none=True)
                        for x in existing.custom_fields
                    ],
                )
            )
        if updated.custom_fields is not None and existing.custom_fields is None:
            patches.append(
                PatchDatum(
                    operation=PatchOperation.ADD,
                    attribute="customFields",
                    new_value=[
                        x.model_dump(by_alias=True, exclude_none=True)
                        for x in updated.custom_fields
                    ],
                )
            )

        # Handle standard field visibility updates
        if updated.standard_field_visibility is not None:
            field_info = EntityTypeStandardFieldVisibility.model_fields
            for field_name, field in field_info.items():
                new_value = getattr(updated.standard_field_visibility, field_name)
                old_value = (
                    getattr(existing.standard_field_visibility, field_name)
                    if existing.standard_field_visibility
                    else None
                )
                if new_value != old_value:
                    # Use the field's alias if available, otherwise use the field name
                    attr_name = field.alias or field_name
                    patches.append(
                        _nested_field_patch(
                            f"standardFieldVisibility.{attr_name}", old_value, new_value
                        )
                    )

        if updated.standard_field_required is not None:
            field_info = EntityTypeStandardFieldRequired.model_fields
            for field_name, field in field_info.items():
                new_value = getattr(updated.standard_field_required, field_name)
                old_value = (
                    getattr(existing.standard_field_required, field_name)
                    if existing.standard_field_required
                    else None
                )
                if new_value != old_value:
                    attr_name = field.alias or field_name
                    patches.append(
                        _nested_field_patch(
                            f"standardFieldRequired.{attr_name}", old_value, new_value
                        )
                    )

        # Handle search query string updates
        if updated.search_query_string is not None:
            field_info = EntityTypeSearchQueryStrings.model_fields
            for field_name, field in field_info.items():
                new_value = getattr(updated.search_query_string, field_name)
                old_value = (
                    getattr(existing.search_query_string, field_name)
                    if existing.search_query_string
                    else None
                )
                if new_value != old_value:
                    # Use the field's alias if available, otherwise use the field name
                    attr_name = field.alias or field_name
                    patches.append(
                        _nested_field_patch(f"searchQueryString.{attr_name}", old_value, new_value)
                    )

        return patches

    @validate_call
    def delete(self, *, id: EntityTypeId) -> None:
        """Delete an entity type by its ID.

        Parameters
        ----------
        id : EntityTypeId
            The Entity Type ID to delete (format ``ETT...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.entity_types.delete(id="ETT1")
        ```
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def get_rules(self, *, id: EntityTypeId) -> list[EntityTypeRule]:
        """Get the conditional field rules configured for an entity type.

        A rule (see [`EntityTypeRule`][albert.resources.entity_types.EntityTypeRule]) makes
        one field's behavior depend on the value of another: for example, showing,
        hiding, requiring, or setting default options on a target field when a
        trigger custom field takes a certain value.

        Parameters
        ----------
        id : EntityTypeId
            The Entity Type ID to get the rules for (format ``ETT...``).

        Returns
        -------
        list[EntityTypeRule]
            The configured rules for the entity type.

        Examples
        --------
        ```python
        rules = client.entity_types.get_rules(id="ETT1")
        [r.id for r in rules]
        # ['RUL1', 'RUL2']
        ```
        """
        response = self.session.get(f"{self.base_path}/rules/{id}")
        return [EntityTypeRule(**rule) for rule in response.json()]

    @validate_call
    def set_rules(self, *, id: EntityTypeId, rules: list[EntityTypeRule]) -> list[EntityTypeRule]:
        """Create or replace the conditional field rules for an entity type.

        This replaces the entity type's full set of rules with the ones provided.
        To read the current rules first, use [`get_rules`][albert.collections.entity_types.EntityTypeCollection.get_rules]; to remove all
        rules, use [`delete_rules`][albert.collections.entity_types.EntityTypeCollection.delete_rules].

        Parameters
        ----------
        id : EntityTypeId
            The Entity Type ID to set the rules for (format ``ETT...``).
        rules : list[EntityTypeRule]
            The rules to apply to the entity type.

        Returns
        -------
        list[EntityTypeRule]
            The updated rules as registered in Albert.

        Examples
        --------
        ```python
        existing = client.entity_types.get_rules(id="ETT1")
        updated = client.entity_types.set_rules(id="ETT1", rules=existing)
        ```
        """
        response = self.session.put(
            f"{self.base_path}/rules/{id}",
            json=[rule.model_dump(exclude_none=True, by_alias=True) for rule in rules],
        )
        return [EntityTypeRule(**rule) for rule in response.json()]

    @validate_call
    def delete_rules(self, *, id: EntityTypeId) -> None:
        """Delete all conditional field rules for an entity type.

        Parameters
        ----------
        id : EntityTypeId
            The Entity Type ID to remove rules from (format ``ETT...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.entity_types.delete_rules(id="ETT1")
        ```
        """
        self.session.delete(f"{self.base_path}/rules/{id}")

    def get_all(
        self,
        *,
        service: EntityServiceType | None = None,
        start_key: str | None = None,
        order: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[EntityType]:
        """Iterate over entity types matching the given filters.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand.

        Parameters
        ----------
        service : EntityServiceType, optional
            Only return entity types associated with this service (e.g. ``tasks``
            or ``inventories``). Defaults to all services.
        start_key : str, optional
            Provide the ``lastKey`` from a previous request to resume pagination.
        order : OrderBy, optional
            Sort direction (ascending or descending). Defaults to the server order.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[EntityType]
            A lazily paginated iterator of matching entity types.

        Examples
        --------
        ```python
        from albert.resources.entity_types import EntityServiceType
        for et in client.entity_types.get_all(
            service=EntityServiceType.INVENTORIES,
            max_items=25,
        ):
            print(et.id, et.label)
        ```
        """
        params = {
            "service": service,
            "limit": max_items,
            "startKey": start_key,
            "orderBy": order,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=lambda items: [EntityType(**item) for item in items],
            max_items=max_items,
        )
