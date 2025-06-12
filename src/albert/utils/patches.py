from copy import deepcopy

from albert.resources.data_templates import DataTemplate
from albert.resources.parameter_groups import (
    EnumValidationValue,
    ParameterGroup,
    ValueValidation,
)
from albert.utils.patch_types import GeneralPatchDatum, PGPatchDatum


def _split_patch_types_for_params_and_data_cols(
    *,
    existing: ParameterGroup | DataTemplate,
    updated: ParameterGroup | DataTemplate,
) -> tuple[list[dict], dict, list[dict]]:
    """Handle special update parameters.

    Parameters
    ----------
    existing : ParameterGroup | DataTemplate
        The existing parameter group or data template.
    updated : ParameterGroup | DataTemplate
        The updated parameter group or data template.

    Returns
    -------
    tuple[list[dict], dict, list[dict]]
        The payload for the special update parameters.
    """

    def normalize_validation(validation):
        """Normalize validation objects for comparison."""
        normalized = []
        for v in validation:
            if isinstance(v.value, list):
                # Normalize EnumValidationValue objects by ignoring `original_text`
                normalized_value = [
                    EnumValidationValue(text=enum.text, id=enum.id, original_text=None)
                    for enum in v.value
                ]
                normalized.append(
                    ValueValidation(
                        datatype=v.datatype,
                        value=normalized_value,
                        min=v.min,
                        max=v.max,
                        operator=v.operator,
                    )
                )
            else:
                normalized.append(v)
        return normalized

    def get_attributes(obj):
        """Map attributes based on the class type."""
        if isinstance(obj, DataTemplate):
            return obj.data_column_values, "column_sequence"
        elif isinstance(obj, ParameterGroup):
            return obj.parameters, "sequence"
        raise TypeError("Unsupported object type")

    def handle_additions(to_add, attribute_name):
        """Handle additions."""
        return [x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in to_add]

    def handle_deletions(to_delete, attribute_name):
        """Handle deletions."""
        return [
            GeneralPatchDatum(operation="delete", attribute=attribute_name, oldValue=sequence)
            for sequence in to_delete
        ]

    def _combine_column_actions_for_data_template(sequence_patches: list[GeneralPatchDatum]):
        """Combine column actions for data template. Pass only a single sequence at a time"""
        combined_patches = []
        actions = []
        for patch in sequence_patches:
            if patch.attribute in ["datacolumn"]:
                # combine actions
                if patch.actions:
                    actions.extend(patch.actions)
            else:
                # units are treated differently
                combined_patches.append(patch)
        if len(actions) > 0:
            combined_patches.append(
                GeneralPatchDatum(
                    attribute="datacolumn",
                    colId=sequence_patches[0].colId,
                    actions=actions,
                )
            )
        return combined_patches

    def handle_updates(to_update, existing_items, updated_items, attribute_name, parent_item):
        """Handle updates."""
        patches = []
        enum_patches = {}

        for sequence in to_update:
            existing_item = next(
                x for x in existing_items if getattr(x, attribute_name) == sequence
            )
            updated_item = next(x for x in updated_items if getattr(x, attribute_name) == sequence)

            # Handle validation updates
            if normalize_validation(existing_item.validation) != normalize_validation(
                updated_item.validation
            ):
                new_patches, new_enum_patches = handle_validation_updates(
                    existing_item, updated_item, sequence, parent_item=parent_item
                )
                patches.extend(new_patches)
                enum_patches[sequence] = new_enum_patches

            # Handle unit updates
            if existing_item.unit != updated_item.unit:
                patches.extend(
                    handle_unit_updates(existing_item, updated_item, sequence, parent_item)
                )

            # Handle value updates
            if existing_item.value != updated_item.value:
                patches.extend(
                    handle_value_updates(existing_item, updated_item, sequence, parent_item)
                )
            if isinstance(parent_item, DataTemplate) and len(patches) > 0:
                patches = _combine_column_actions_for_data_template(patches)

        return patches, enum_patches

    def handle_tags(existing_tags, updated_tags, attr_name: str):
        """Handle tags updates."""
        patches = []
        existing_tag_ids = [x.id for x in existing_tags] if existing_tags else []
        updated_tag_ids = [x.id for x in updated_tags] if updated_tags else []
        # Add new tags
        for tag in updated_tag_ids:
            if tag not in (existing_tag_ids):
                patches.append(
                    PGPatchDatum(
                        operation="add",
                        attribute=attr_name,
                        newValue=tag,
                    )
                )

        # Remove old tags
        for tag in existing_tag_ids:
            if tag not in (updated_tag_ids):
                patches.append(
                    PGPatchDatum(
                        operation="delete",
                        attribute=attr_name,
                        oldValue=tag,
                    )
                )

        return patches

    def handle_validation_updates(existing_item, updated_item, sequence, parent_item):
        """Handle validation updates."""
        patches = []
        enum_patches = []

        existing_item = deepcopy(existing_item)
        updated_item = deepcopy(updated_item)

        # Handle enum validations
        if isinstance(updated_item.validation[0].value, list):
            existing_enums = (
                []
                if existing_item.validation is None
                or not isinstance(existing_item.validation[0].value, list)
                else existing_item.validation[0].value
            )
            updated_enums = (
                [] if updated_item.validation is None else updated_item.validation[0].value
            )

            existing_enum_names = [
                x.text for x in existing_enums if isinstance(x, EnumValidationValue)
            ]
            updated_enum_names = [
                x.text for x in updated_enums if isinstance(x, EnumValidationValue)
            ]

            # Add new enum values
            new_enum_names = set(updated_enum_names) - set(existing_enum_names)
            deleted_enum_names = set(existing_enum_names) - set(updated_enum_names)
            for new_enum_name in new_enum_names:
                enum_patches.append(
                    {
                        "operation": "add",
                        "text": new_enum_name,
                    }
                )
            for deleted_enum in deleted_enum_names:
                deleted_enum = [x for x in existing_enums if x.text == deleted_enum][0]
                enum_patches.append(
                    {
                        "operation": "delete",
                        "id": deleted_enum.id,
                    }
                )

        for i, validation in enumerate(updated_item.validation):
            # If `value` is a list, set it to `None` before dumping because those are enums and are handled above
            if isinstance(validation.value, list):
                updated_item.validation[i].value = None

        for i, validation in enumerate(existing_item.validation):
            # If `value` is a list, set it to `None` before dumping because those are enums and are handled above
            if isinstance(validation.value, list):
                existing_item.validation[i].value = None
        if normalize_validation(existing_item.validation) != normalize_validation(
            updated_item.validation
        ):
            # If there are non-emum validation changes, handle them\
            if isinstance(parent_item, ParameterGroup):
                patch = GeneralPatchDatum(
                    operation="update",
                    attribute="validation",
                    oldValue=[
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in existing_item.validation
                    ],
                    newValue=[
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in updated_item.validation
                    ],
                    rowId=sequence,
                )
                patches.append(patch)

            elif isinstance(parent_item, DataTemplate):
                patch = GeneralPatchDatum(
                    attribute="datacolumn",
                    actions=[
                        GeneralPatchDatum(
                            operation="update",
                            attribute="validation",
                            oldValue=[
                                x.model_dump(mode="json", by_alias=True, exclude_none=True)
                                for x in existing_item.validation
                            ],
                            newValue=[
                                x.model_dump(mode="json", by_alias=True, exclude_none=True)
                                for x in updated_item.validation
                            ],
                            colId=sequence,
                        )
                    ],
                    colId=sequence,
                )
                patches.append(patch)

        return (patches, enum_patches)

    def handle_unit_updates(existing_item, updated_item, sequence, parent_item):
        """Handle unit updates."""
        patches = []
        attribute_name = "unitId" if isinstance(parent_item, ParameterGroup) else "unit"
        if existing_item.unit is None:
            patch = GeneralPatchDatum(
                operation="add",
                attribute=attribute_name,
                newValue=updated_item.unit.id,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence
                patches.append(patch)
            else:
                # ParameterGroup
                patches.append(patch)
        elif updated_item.unit is None:
            patch = GeneralPatchDatum(
                operation="delete",
                attribute=attribute_name,
                oldValue=existing_item.unit.id,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence

            patches.append(patch)

        elif existing_item.unit.id != updated_item.unit.id:
            patch = GeneralPatchDatum(
                operation="update",
                attribute=attribute_name,
                oldValue=existing_item.unit.id,
                newValue=updated_item.unit.id,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence
            patches.append(patch)
        return patches

    def handle_value_updates(existing_item, updated_item, sequence, parent_item):
        """Handle value updates."""
        patches = []
        if isinstance(updated_item.value, list):
            # then this is an Emum and needs to be handled differently
            return patches
        if existing_item.value is None:
            patch = GeneralPatchDatum(
                operation="add",
                attribute="value",
                newValue=updated_item.value,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence
            if isinstance(parent_item, DataTemplate):
                patch = GeneralPatchDatum(
                    operation="add",
                    actions=[patch],
                    colId=sequence,
                    attribute="datacolumn",
                )
                patches.append(patch)
            else:
                # ParameterGroup
                patches.append(patch)
        elif updated_item.value is None:
            patch = GeneralPatchDatum(
                operation="delete",
                attribute="value",
                oldValue=existing_item.value,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence
            if isinstance(parent_item, DataTemplate):
                patches.append(
                    GeneralPatchDatum(
                        operation="delete",
                        actions=[patch],
                        colId=sequence,
                        attribute="datacolumn",
                    )
                )
            else:
                # ParameterGroup
                patches.append(patch)
        else:
            patch = GeneralPatchDatum(
                operation="update",
                attribute="value",
                oldValue=existing_item.value,
                newValue=updated_item.value,
            )
            if isinstance(parent_item, ParameterGroup):
                patch.rowId = sequence
            elif isinstance(parent_item, DataTemplate):
                patch.colId = sequence
            if isinstance(parent_item, DataTemplate):
                patches.append(
                    GeneralPatchDatum(
                        operation="update",
                        actions=[patch],
                        colId=sequence,
                        attribute="datacolumn",
                    )
                )
            else:
                # ParameterGroup
                patches.append(patch)
        return patches

    # Main logic
    existing_items, attribute_name = get_attributes(existing)
    updated_items, _ = get_attributes(updated)

    existing_sequences = [getattr(x, attribute_name) for x in existing_items]
    updated_sequences = [getattr(x, attribute_name) for x in updated_items]

    to_add = [x for x in updated_items if getattr(x, attribute_name) not in existing_sequences]
    to_delete = set(existing_sequences) - set(updated_sequences)
    to_update = set(existing_sequences) & set(updated_sequences)

    new_param_patches = handle_additions(to_add, attribute_name)
    deletion_patches = handle_deletions(to_delete, attribute_name)
    update_patches, enum_patches = handle_updates(
        to_update, existing_items, updated_items, attribute_name, parent_item=updated
    )

    # Handle tags at the object level
    tag_patches = handle_tags(
        existing.tags,
        updated.tags,
        attr_name="tagId" if isinstance(updated, ParameterGroup) else "tag",
    )

    return deletion_patches + update_patches + tag_patches, enum_patches, new_param_patches
