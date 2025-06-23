from deprecated import deprecated

from albert.core.session import AlbertSession
from albert.resources.common.models import BaseResource, MetadataItem
from albert.resources.common.patch import PatchDatum, PatchOperation, PatchPayload


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
            if key not in updated_metadata:
                if isinstance(value, str | int | float):
                    data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.DELETE,
                            old_value=value,
                        )
                    )
                elif isinstance(value, list):
                    for v in value:
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.DELETE,
                                old_value=v.id,
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
                    to_add = updated_id - existing_id
                    to_remove = existing_id - updated_id

                    for v in to_add:
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.ADD,
                                new_value=v,
                            )
                        )
                    for v in to_remove:
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.DELETE,
                                old_value=v,
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
                    for v in value:
                        data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.ADD,
                                new_value=v.id,
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
                alias = existing.__class__.model_fields[attribute].alias or attribute

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

    @deprecated(
        "The 'list' method is deprecated and no longer supported. Use 'get_all(params=...)' or 'search(...)' instead.",
        version="1.0.0",
    )
    def list(self, **kwargs):
        raise NotImplementedError(
            "The 'list' method is deprecated and has been disabled. "
            "Use 'get_all(params=...)' or 'search(...)' instead."
        )
