from albert.core.session import AlbertSession
from albert.core.shared.models.base import BaseResource
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
                            old_value=all_ids[0] if len(all_ids) == 1 else all_ids,
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
                    existing_id = {v.id for v in value} if isinstance(value, list) else {value.id}
                    updated_id = {v.id for v in updated_metadata[key]}
                    to_add = list(updated_id - existing_id)
                    to_remove = list(existing_id - updated_id)
                    if len(to_add + to_remove) == 0:  # if there are no changes, skip
                        continue

                    # Handle additions and removals separately to avoid conflicts

                    if len(to_remove) > 0:
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.DELETE,
                                old_value=to_remove,
                            )
                        )

                    if len(to_add) > 0:
                        data.append(
                            PatchDatum(
                                attribute=attribute, operation=PatchOperation.ADD, new_value=to_add
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
                            new_value=all_ids[0] if len(all_ids) == 1 else all_ids,
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
        """Generate a payload for PATCH requests based on the changes.

        This is overriden for some clases with more compex patch formation.
        """
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
