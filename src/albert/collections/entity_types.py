from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import EntityTypeId
from albert.core.shared.models.patch import PatchDatum, PatchOperation
from albert.resources.entity_types import EntityServiceType, EntityType, EntityTypeRule


class EntityTypeCollection(BaseCollection):
    """A collection of configurable entity types in the Albert system.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    """

    _api_version = "v3"
    _updatable_attributes = {
        "label",
        "template_based",
        "locked_template",
        "custom_fields",
        "standard_field_visibility",
        "search_query_string",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize the EntityTypeCollection with the provided session."""
        super().__init__(session=session)
        self.base_path = f"/api/{EntityTypeCollection._api_version}/entitytypes"

    def get_by_id(self, *, id: EntityTypeId) -> EntityType:
        """Get an entity type by its ID.
        Parameters
        ----------
        id : EntityTypeId
            The ID of the entity type to get.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return EntityType(**response.json())

    def create(self, *, entity_type: EntityType) -> EntityType:
        """Create an entity type.
        Parameters
        ----------
        entity_type : EntityType
            The entity type to create.
        """
        response = self.session.post(
            self.base_path, json=entity_type.model_dump(by_alias=True, exclude_none=True)
        )
        return EntityType(**response.json())

    def update(self, *, entity_type: EntityType) -> EntityType:
        """Update an entity type.
        Parameters
        ----------
        entity_type : EntityType
            The entity type to update.
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
        if updated.custom_fields is not None and existing.custom_fields is not None:
            patches.append(
                PatchDatum(
                    operation=PatchOperation.UPDATE,
                    attribute="customFields",
                    new_value=[x.model_dump(by_alias=True) for x in updated.custom_fields],
                    old_value=[x.model_dump(by_alias=True) for x in existing.custom_fields],
                )
            )
        if updated.custom_fields is not None and existing.custom_fields is None:
            patches.append(
                PatchDatum(
                    operation=PatchOperation.ADD,
                    attribute="customFields",
                    new_value=[x.model_dump(by_alias=True) for x in updated.custom_fields],
                )
            )

        # Handle standard field visibility updates
        if updated.standard_field_visibility is not None:
            field_info = updated.standard_field_visibility.model_fields
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
                        PatchDatum(
                            operation=PatchOperation.UPDATE,
                            attribute=f"standardFieldVisibility.{attr_name}",
                            new_value=new_value,
                            old_value=old_value,
                        )
                    )

        # Handle search query string updates
        if updated.search_query_string is not None:
            field_info = updated.search_query_string.model_fields
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
                        PatchDatum(
                            operation=PatchOperation.UPDATE,
                            attribute=f"searchQueryString.{attr_name}",
                            new_value=new_value,
                            old_value=old_value,
                        )
                    )

        return patches

    def delete(self, *, id: EntityTypeId) -> None:
        """Delete an entity type.
        Parameters
        ----------
        id : EntityTypeId
            The ID of the entity type to delete.
        """
        self.session.delete(f"{self.base_path}/{id}")

    def get_rules(self, *, id: EntityTypeId) -> list[EntityTypeRule]:
        """Get the rules for an entity type.
        Parameters
        ----------
        id : EntityTypeId
            The ID of the entity type to get the rules for.
        """
        response = self.session.get(f"{self.base_path}/rules/{id}")
        return [EntityTypeRule(**rule) for rule in response.json()]

    def set_rules(self, *, id: EntityTypeId, rules: list[EntityTypeRule]) -> list[EntityTypeRule]:
        """Create or update the rules for an entity type.
        Parameters
        ----------
        id : EntityTypeId
            The ID of the entity type to update the rules for.
        rules : list[EntityTypeRule]
            The rules to update.
        Returns
        -------
        list[EntityTypeRule]
            The updated rules.
        """
        response = self.session.put(
            f"{self.base_path}/rules/{id}",
            json=[rule.model_dump(exclude_none=True, by_alias=True) for rule in rules],
        )
        return [EntityTypeRule(**rule) for rule in response.json()]

    def delete_rules(self, *, id: EntityTypeId) -> None:
        """Delete the rules for an entity type.
        Parameters
        ----------
        id : EntityTypeId
            The ID of the entity type to delete the rules for.
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
        """Searches for EntityType items based on the provided parameters.
        Parameters
        ----------
        service : EntityServiceType | None, optional
            The service type the entity type is associated with, by default None
        limit : int, optional
            Maximum number of results to return, by default 100
        start_key : str | None, optional
            Key to start pagination from, by default None
        order : OrderBy | None, optional
            Sort order (ascending/descending), by default None
        Yields
        ------
        Iterator[EntityType]
            Returns an iterator of EntityType items matching the search criteria.
        """
        params = {
            "service": service.value if service else None,
            "limit": max_items,
            "startKey": start_key,
            "order": order.value if order else None,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=lambda items: [EntityType(**item) for item in items],
            max_items=max_items,
        )
