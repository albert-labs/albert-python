from typing import Any

from albert.core.session import AlbertSession
from albert.core.shared.models.base import BaseResource, EntityLink
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.shared.types import MetadataItem


class BaseCollection:
    """
    BaseCollection is the base class for all collection classes.

    Parameters
    ----------
    session : AlbertSession
        The Albert API Session instance.
    """

    # Class property specifying updatable attributes
    _updatable_attributes = {}

    def __init__(self, *, session: AlbertSession):
        self.session = session

    def _metadata_list_patch_value(self, links: list[EntityLink], *, as_list: bool = False) -> Any:
        """Serialize list metadata for PATCH. Override in subclasses when needed.

        Default behavior sends bare list IDs. CasCollection overrides this to send
        entity-link objects because the CAS API does not normalize list metadata IDs.
        """
        all_ids = [link.id for link in links]
        if as_list:
            return all_ids
        return all_ids[0] if len(all_ids) == 1 else all_ids

    def _generate_metadata_diff(
        self,
        existing_metadata: dict[str, MetadataItem],
        updated_metadata: dict[str, MetadataItem],
    ) -> list[PatchDatum]:
        if existing_metadata is None:
            existing_metadata = {}
        if updated_metadata is None:
            updated_metadata = {}
        data = []
        for key, value in existing_metadata.items():
            attribute = f"Metadata.{key}"
            if key not in updated_metadata or updated_metadata[key] is None:
                if isinstance(value, str | int | float):
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.DELETE,
                            old_value=value,
                        )
                    )
                elif isinstance(value, list):
                    all_ids = [x.id for x in value]
                    if len(all_ids) == 0:
                        continue

                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.DELETE,
                            old_value=self._metadata_list_patch_value(value),
                        )
                    )
                else:
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.DELETE,
                            old_value=value.id,
                        )
                    )
            elif value != updated_metadata[key]:
                if isinstance(updated_metadata[key], str | int | float):
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.UPDATE,
                            old_value=value,
                            new_value=updated_metadata[key],
                        )
                    )
                elif isinstance(updated_metadata[key], list):
                    existing_links = value if isinstance(value, list) else [value]
                    updated_links = updated_metadata[key]
                    existing_ids = [v.id for v in existing_links]
                    updated_ids = [v.id for v in updated_links]
                    if set(existing_ids) == set(updated_ids):  # no membership change, skip
                        continue

                    if len(updated_ids) == 0:
                        # Clearing the value entirely.
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.DELETE,
                                old_value=self._metadata_list_patch_value(
                                    existing_links, as_list=True
                                ),
                            )
                        )
                    else:
                        # Replace the whole list in a single update. Emitting a
                        # delete followed by an add would briefly leave the field
                        # empty, which the backend rejects for required fields.
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.UPDATE,
                                old_value=self._metadata_list_patch_value(
                                    existing_links, as_list=True
                                ),
                                new_value=self._metadata_list_patch_value(
                                    updated_links, as_list=True
                                ),
                            )
                        )
                else:
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.UPDATE,
                            old_value=value.id,
                            new_value=updated_metadata[key].id,
                        )
                    )
        for key, value in updated_metadata.items():
            attribute = f"Metadata.{key}"
            if key not in existing_metadata:
                if isinstance(value, str | int | float):
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.ADD,
                            new_value=value,
                        )
                    )
                elif isinstance(value, list):
                    all_ids = [x.id for x in value]
                    if len(all_ids) == 0:
                        continue
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.ADD,
                            new_value=self._metadata_list_patch_value(value),
                        )
                    )
                else:
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.ADD,
                            new_value=value.id,
                        )
                    )

        return data

    def _generate_patch_payload(
        self,
        *,
        existing: BaseResource,
        updated: BaseResource,
        generate_metadata_diff: bool = True,
        stringify_values: bool = False,
    ) -> PatchPayload:
        """Generate PATCH request data based on the changes.

        This is overriden for some clases with more compex patch formation.
        """
        data = []
        for attribute in self._updatable_attributes:
            old_value = getattr(existing, attribute, None)
            new_value = getattr(updated, attribute, None)
            # A field the caller never set is left untouched: only an explicitly
            # provided value participates in the diff. This prevents omitted fields
            # from being read as deletions (an unset value is distinct from an
            # explicit None or []), including fields whose type has a non-None default.
            if attribute not in updated.model_fields_set:
                continue
            # Sometimes None and empty lists/dicts are serilized/deserilized to the same value, but wont look the same here
            if old_value is None and (new_value == [] or new_value == {}):
                # Avoid updating None to an empty list
                new_value = None
            elif (old_value == [] or old_value == {}) and new_value is None:
                # Avoid updating an empty list to None
                old_value = None
            if attribute == "metadata" and generate_metadata_diff:
                data.extend(
                    self._generate_metadata_diff(
                        existing_metadata=old_value,
                        updated_metadata=new_value,
                    )
                )
            else:
                # Get the serialization alias name for the attribute, if it exists
                field_info = existing.__class__.model_fields[attribute]
                alias = (
                    getattr(field_info, "serialization_alias", None)
                    or field_info.alias
                    or attribute
                )

                if old_value is None and new_value is not None:
                    # Add new attribute
                    new_value = str(new_value) if stringify_values else new_value
                    data.append(
                        PatchDatum(
                            attribute=alias,
                            operation=PatchOperation.ADD,
                            new_value=new_value,
                        )
                    )
                if new_value is None and old_value is not None:
                    # Delete the attribute
                    data.append(
                        PatchDatum(
                            attribute=alias, operation=PatchOperation.DELETE, old_value=old_value
                        )
                    )
                elif old_value is not None and new_value != old_value:
                    # Update existing attribute
                    old_value = str(old_value) if stringify_values else old_value
                    new_value = str(new_value) if stringify_values else new_value
                    data.append(
                        PatchDatum(
                            attribute=alias,
                            operation=PatchOperation.UPDATE,
                            old_value=old_value,
                            new_value=new_value,
                        )
                    )
        return PatchPayload(data=data)
