from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.custom_fields import CustomField


def _generate_custom_field_patch_payload(
    *, existing: CustomField, updated: CustomField, updatable_attributes: set[str]
) -> PatchPayload:
    data: list[PatchDatum] = []
    for attribute in updatable_attributes:
        old_value = getattr(existing, attribute, None)
        new_value = getattr(updated, attribute, None)

        # Treat None and empty containers as equivalent for patch generation.
        if old_value is None and (new_value == [] or new_value == {}):
            new_value = None
        elif (old_value == [] or old_value == {}) and new_value is None:
            old_value = None

        field_info = existing.__class__.model_fields[attribute]
        alias = getattr(field_info, "serialization_alias", None) or field_info.alias or attribute

        if alias == "entityCategory":
            # Backend expects item-level add/delete operations for entityCategory.
            data.extend(
                _generate_entity_category_patches(
                    attribute=alias, old_value=old_value, new_value=new_value
                )
            )
            continue

        if alias == "customEntityCategory":
            # customEntityCategory has slightly different API semantics than entityCategory.
            data.extend(
                _generate_custom_entity_category_patches(
                    attribute=alias, old_value=old_value, new_value=new_value
                )
            )
            continue

        if old_value is None and new_value is not None:
            operation = (
                PatchOperation.UPDATE
                if alias in ("hidden", "search", "lkpColumn", "lkpRow")
                else PatchOperation.ADD
            )
            data.append(
                PatchDatum(
                    attribute=alias,
                    operation=operation,
                    old_value=False if operation == PatchOperation.UPDATE else None,
                    new_value=new_value,
                )
            )
        elif new_value is None and old_value is not None:
            data.append(
                PatchDatum(
                    attribute=alias,
                    operation=PatchOperation.DELETE,
                    old_value=old_value,
                )
            )
        elif old_value is not None and new_value != old_value:
            data.append(
                PatchDatum(
                    attribute=alias,
                    operation=PatchOperation.UPDATE,
                    old_value=old_value,
                    new_value=new_value,
                )
            )

    return PatchPayload(data=data)


def _generate_entity_category_patches(
    *, attribute: str, old_value: list | None, new_value: list | None
) -> list[PatchDatum]:
    old_values = old_value or []
    new_values = new_value or []

    # Build a minimal diff instead of sending full-list updates.
    to_delete = [v for v in old_values if v not in new_values]
    to_add = [v for v in new_values if v not in old_values]

    patches = [
        PatchDatum(attribute=attribute, operation=PatchOperation.DELETE, old_value=value)
        for value in to_delete
    ]
    patches.extend(
        [
            PatchDatum(attribute=attribute, operation=PatchOperation.ADD, new_value=value)
            for value in to_add
        ]
    )
    return patches


def _generate_custom_entity_category_patches(
    *, attribute: str, old_value: list | None, new_value: list | None
) -> list[PatchDatum]:
    # Initial population is sent as UPDATE with [] oldValue.
    if old_value is None and isinstance(new_value, list):
        return [
            PatchDatum(
                attribute=attribute,
                operation=PatchOperation.UPDATE,
                old_value=[],
                new_value=value,
            )
            for value in new_value
        ]
    if old_value is not None and new_value is None:
        return [
            PatchDatum(attribute=attribute, operation=PatchOperation.DELETE, old_value=old_value)
        ]
    if old_value != new_value:
        return [
            PatchDatum(
                attribute=attribute,
                operation=PatchOperation.UPDATE,
                old_value=old_value,
                new_value=new_value,
            )
        ]
    return []
