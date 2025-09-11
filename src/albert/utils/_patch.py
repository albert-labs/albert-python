from copy import deepcopy

from albert.core.shared.models.patch import (
    DTPatchDatum,
    GeneralPatchDatum,
    PatchDatum,
    PatchPayload,
    PGPatchDatum,
    PGPatchPayload,
)
from albert.resources.data_templates import DataColumnValue, DataTemplate
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    ParameterGroup,
    ParameterValue,
)
from albert.resources.tags import Tag


def _normalize_validation(validation: list[EnumValidationValue]) -> list[EnumValidationValue]:
    """Normalize validation objects for comparison. Ignore original_text for enum values."""
    normalized = []
    for v in validation:
        if isinstance(v.value, list):
            normalized_value = [
                EnumValidationValue(text=enum.text, id=enum.id, original_text=None)
                for enum in v.value
            ]
            v.value = normalized_value
        normalized.append(v)
    return normalized


def _parameter_unit_patches(
    initial_parameter_value: ParameterValue, updated_parameter_value: ParameterValue
) -> PGPatchDatum | None:
    """Generate unit patch for a parameter value."""

    if initial_parameter_value.unit == updated_parameter_value.unit:
        return None
    if initial_parameter_value.unit is None:
        if updated_parameter_value.unit is not None:
            return PGPatchDatum(
                operation="add",
                attribute="unitId",
                newValue=updated_parameter_value.unit.id,
                rowId=updated_parameter_value.sequence,
            )
    elif updated_parameter_value.unit is None:
        if initial_parameter_value.unit is not None:
            return PGPatchDatum(
                operation="delete",
                attribute="unitId",
                oldValue=initial_parameter_value.unit.id,
                rowId=updated_parameter_value.sequence,
            )
    elif initial_parameter_value.unit.id != updated_parameter_value.unit.id:
        return PGPatchDatum(
            operation="update",
            attribute="unitId",
            oldValue=initial_parameter_value.unit.id,
            newValue=updated_parameter_value.unit.id,
            rowId=updated_parameter_value.sequence,
        )
    return None


def _data_column_unit_patches(
    initial_data_column_value: DataColumnValue, updated_data_column_value: DataColumnValue
) -> DTPatchDatum | None:
    """Generate unit patch for a data column value."""

    if initial_data_column_value.unit == updated_data_column_value.unit:
        return None
    elif initial_data_column_value.unit is None:
        if updated_data_column_value.unit is not None:
            return DTPatchDatum(
                operation="add",
                attribute="unit",
                newValue=updated_data_column_value.unit.id,
                colId=initial_data_column_value.sequence,
            )

    elif updated_data_column_value.unit is None:
        if initial_data_column_value.unit is not None:
            return DTPatchDatum(
                operation="delete",
                attribute="unit",
                oldValue=initial_data_column_value.unit.id,
                colId=initial_data_column_value.sequence,
            )
    elif initial_data_column_value.unit.id != updated_data_column_value.unit.id:
        return DTPatchDatum(
            operation="update",
            attribute="unit",
            oldValue=initial_data_column_value.unit.id,
            newValue=updated_data_column_value.unit.id,
            colId=initial_data_column_value.sequence,
        )
    return None


def _parameter_value_patches(
    initial_parameter_value: ParameterValue, updated_parameter_value: ParameterValue
) -> PGPatchDatum | None:
    """Generate a Patch for a parameter value."""

    if initial_parameter_value.value == updated_parameter_value.value:
        return None
    elif initial_parameter_value.value is None:
        if updated_parameter_value.value is not None:
            return PGPatchDatum(
                operation="add",
                attribute="value",
                newValue=updated_parameter_value.value,
                rowId=updated_parameter_value.sequence,
            )
    elif updated_parameter_value.value is None:
        if initial_parameter_value.value is not None:
            return PGPatchDatum(
                operation="delete",
                attribute="value",
                oldValue=initial_parameter_value.value,
                rowId=updated_parameter_value.sequence,
            )
    elif initial_parameter_value.value != updated_parameter_value.value:
        return PGPatchDatum(
            operation="update",
            attribute="value",
            oldValue=initial_parameter_value.value,
            newValue=updated_parameter_value.value,
            rowId=updated_parameter_value.sequence,
        )
    return None


def _data_column_value_patches(
    initial_data_column_value: DataColumnValue, updated_data_column_value: DataColumnValue
) -> DTPatchDatum | None:
    """Generate a Patch for a data column value."""
    if initial_data_column_value.value == updated_data_column_value.value:
        return None
    elif initial_data_column_value.value is None:
        if updated_data_column_value.value is not None:
            return DTPatchDatum(
                operation="add",
                attribute="value",
                newValue=updated_data_column_value.value,
                colId=initial_data_column_value.sequence,
            )
    elif updated_data_column_value.value is None:
        if initial_data_column_value.value is not None:
            return DTPatchDatum(
                operation="delete",
                attribute="value",
                oldValue=initial_data_column_value.value,
                colId=initial_data_column_value.sequence,
            )
    elif initial_data_column_value.value != updated_data_column_value.value:
        return DTPatchDatum(
            operation="update",
            attribute="value",
            oldValue=initial_data_column_value.value,
            newValue=updated_data_column_value.value,
            colId=initial_data_column_value.sequence,
        )
    return None


def data_column_validation_patches(
    initial_data_column: DataColumnValue, updated_data_column: DataColumnValue
) -> DTPatchDatum | None:
    """Generate validation patches for a data column."""
    if initial_data_column.validation == updated_data_column.validation:
        return None
    elif initial_data_column.validation is None and updated_data_column.validation is not None:
        return DTPatchDatum(
            operation="add", attribute="validation", newValue=updated_data_column.validation
        )
    elif updated_data_column.validation is None and initial_data_column.validation is not None:
        return DTPatchDatum(
            operation="delete", attribute="validation", oldValue=initial_data_column.validation
        )
    # We need to clear enum values without modifying anything in memory
    initial_data_column_copy = deepcopy(initial_data_column)
    updated_data_column_copy = deepcopy(updated_data_column)

    if (
        initial_data_column_copy.validation
        and len(initial_data_column_copy.validation) == 1
        and initial_data_column_copy.validation[0].datatype == DataType.ENUM
    ):
        initial_data_column_copy.validation[0].value = None
    if (
        updated_data_column_copy.validation
        and len(updated_data_column_copy.validation) == 1
        and updated_data_column_copy.validation[0].datatype == DataType.ENUM
    ):
        updated_data_column_copy.validation[0].value = None
    if initial_data_column_copy.validation != updated_data_column_copy.validation:
        return DTPatchDatum(
            operation="update",
            attribute="validation",
            oldValue=initial_data_column.validation,
            newValue=updated_data_column.validation,
        )
    return None


def parameter_validation_patch(
    initial_parameter: ParameterValue, updated_parameter: ParameterValue
) -> PGPatchDatum | None:
    """Generate validation patches for a parameter."""

    # We need to clear enum values without modifying anything in memory
    if initial_parameter.validation == updated_parameter.validation:
        return None
    initial_parameter_copy = deepcopy(initial_parameter)
    updated_parameter_copy = deepcopy(updated_parameter)
    if (
        initial_parameter_copy.validation
        and len(initial_parameter_copy.validation) == 1
        and initial_parameter_copy.validation[0].datatype == DataType.ENUM
    ):
        initial_parameter_copy.validation[0].value = None
    if (
        updated_parameter_copy.validation
        and len(updated_parameter_copy.validation) == 1
        and updated_parameter_copy.validation[0].datatype == DataType.ENUM
    ):
        updated_parameter_copy.validation[0].value = None
    if initial_parameter_copy.validation == updated_parameter_copy.validation:
        return None
    if initial_parameter_copy.validation is None:
        if updated_parameter_copy.validation is not None:
            return PGPatchDatum(
                operation="add",
                attribute="validation",
                newValue=updated_parameter.validation,
                rowId=updated_parameter.sequence,
            )
    elif updated_parameter_copy.validation is None:
        if initial_parameter_copy.validation is not None:
            return PGPatchDatum(
                operation="delete",
                attribute="validation",
                oldValue=initial_parameter.validation,
                rowId=updated_parameter.sequence,
            )
    elif initial_parameter_copy.validation != updated_parameter_copy.validation:
        return PGPatchDatum(
            operation="update",
            attribute="validation",
            newValue=updated_parameter.validation,
            rowId=updated_parameter.sequence,
        )
    return None


def generate_data_column_patches(
    initial_data_column: list[DataColumnValue] | None,
    updated_data_column: list[DataColumnValue] | None,
) -> tuple[list[DTPatchDatum], list[DataColumnValue], dict[str, list[dict]]]:
    """Generate patches for a data column.
    Returns a group of patches as well as the data column values to add/put
    """
    if initial_data_column is None:
        initial_data_column = []
    if updated_data_column is None:
        updated_data_column = []
    patches = []
    enum_patches = {}
    new_data_columns = [
        x
        for x in updated_data_column
        if x.sequence not in [y.sequence for y in initial_data_column] or not x.sequence
    ]
    deleted_data_columns = [
        x
        for x in initial_data_column
        if x.sequence not in [y.sequence for y in updated_data_column]
    ]
    updated_data_columns = [
        x for x in updated_data_column if x.sequence in [y.sequence for y in initial_data_column]
    ]
    for del_dc in deleted_data_columns:
        patches.append(
            DTPatchDatum(operation="delete", attribute="datacolumn", oldValue=del_dc.sequence)
        )

    for updated_dc in updated_data_columns:
        these_actions = []
        initial_dc = next(x for x in initial_data_column if x.sequence == updated_dc.sequence)
        # unit_patch = _data_column_unit_patches(initial_dc, updated_dc)
        value_patch = _data_column_value_patches(initial_dc, updated_dc)
        validation_patch = data_column_validation_patches(initial_dc, updated_dc)
        # if unit_patch:
        #     these_actions.append(unit_patch)
        if value_patch:
            these_actions.append(value_patch)
        if validation_patch:
            these_actions.append(validation_patch)
        # actions cannot have colId, so we need to remove it
        for action in these_actions:
            action.colId = None
        if len(these_actions) > 0:
            this_patch = GeneralPatchDatum(
                attribute="datacolumn",
                actions=these_actions,
                colId=updated_dc.sequence,
            )
            patches.append(this_patch)

        unit_patch = _data_column_unit_patches(initial_dc, updated_dc)
        if unit_patch:
            patches.append(unit_patch)

        if (
            updated_dc.validation is not None
            and updated_dc.validation != []
            and updated_dc.validation[0].datatype == DataType.ENUM
        ):
            enum_patches[updated_dc.sequence] = generate_enum_patches(
                existing_enums=initial_dc.validation[0].value,
                updated_enums=updated_dc.validation[0].value,
            )
    return patches, new_data_columns, enum_patches


def generate_enum_patches(
    existing_enums: list[EnumValidationValue], updated_enums: list[EnumValidationValue]
) -> list[dict]:
    """Generate enum patches for a data column or parameter validation."""

    if existing_enums is None:
        existing_enums = []
    if updated_enums is None:
        updated_enums = []
    existing_enums = [x for x in existing_enums if isinstance(x, EnumValidationValue)]
    updated_enums = [x for x in updated_enums if isinstance(x, EnumValidationValue)]
    existing_lookup = {x.text: x for x in existing_enums}
    existing_ids = {x.id for x in existing_enums if x.id is not None}

    rehydrated_updated_enums = []
    for e in updated_enums:
        if e.id is not None:
            rehydrated_updated_enums.append(e)
            continue
        else:
            # look for the enum in existing_enums
            if e.text in existing_lookup:
                e = existing_lookup[e.text]
            rehydrated_updated_enums.append(e)

    updated_enums = rehydrated_updated_enums
    enums_in_both = [x for x in updated_enums if x.id is not None and x.id in existing_ids]
    if existing_enums == updated_enums:
        return []
    enum_patches = []

    existing_enums_values = [x for x in existing_enums if isinstance(x, EnumValidationValue)]

    enums_in_both = [x for x in enums_in_both if isinstance(x, EnumValidationValue)]

    updated_enum_ids = [x.id for x in updated_enums if x.id is not None]

    deleted_enums = [
        x for x in existing_enums if x.id is not None and x.id not in updated_enum_ids
    ]
    new_enums = [x for x in updated_enums if x.id is None or x.id not in existing_ids]
    enums_with_new_names = []
    for enum_to_check in enums_in_both:
        initial_enum = next(x for x in existing_enums_values if x.id == enum_to_check.id)
        if initial_enum.text != enum_to_check.text:
            enums_with_new_names.append(enum_to_check)

    for new_enum in new_enums:
        enum_patches.append({"operation": "add", "text": new_enum.text})
    for deleted_enum in deleted_enums:
        enum_patches.append({"operation": "delete", "id": deleted_enum.id})
    for updated_enum in enums_with_new_names:
        enum_patches.append(
            {"operation": "update", "id": updated_enum.id, "text": updated_enum.text}
        )

    return enum_patches


def generate_parameter_patches(
    initial_parameters: list[ParameterValue] | None,
    updated_parameters: list[ParameterValue] | None,
    parameter_attribute_name: str = "parameter",
) -> tuple[list[PGPatchDatum], list[ParameterValue], dict[str, list[dict]]]:
    """Generate patches for a parameter."""
    parameter_patches = []
    enum_patches = {}
    if initial_parameters is None:
        initial_parameters = []
    if updated_parameters is None:
        updated_parameters = []

    initial_seq_map = {p.sequence: p for p in initial_parameters if p.sequence}
    initial_id_map = {p.id: p for p in initial_parameters}

    updated_param_pairs = []  # tuple of (initial, updated)
    new_parameters = []

    # Match updated parameters to initial ones
    for p_updated in updated_parameters:
        p_initial = None
        # match by sequence if available
        if p_updated.sequence and p_updated.sequence in initial_seq_map:
            p_initial = initial_seq_map[p_updated.sequence]
        # matching by ID if sequence is missing on the updated param
        elif not p_updated.sequence and p_updated.id in initial_id_map:
            p_initial = initial_id_map[p_updated.id]
            if p_initial.sequence:
                p_updated.sequence = p_initial.sequence

        if p_initial:
            updated_param_pairs.append((p_initial, p_updated))
        else:
            new_parameters.append(p_updated)

    updated_matched_sequences = {p_updated.sequence for _, p_updated in updated_param_pairs}
    deleted_parameters = [
        p for p in initial_parameters if p.sequence not in updated_matched_sequences
    ]

    if len(deleted_parameters) > 0:
        parameter_patches.append(
            PGPatchDatum(
                operation="delete",
                attribute=parameter_attribute_name,
                oldValue=[x.sequence for x in deleted_parameters],
            )
        )
    for existing_param, updated_param in updated_param_pairs:
        unit_patch = _parameter_unit_patches(existing_param, updated_param)
        value_patch = _parameter_value_patches(existing_param, updated_param)
        validation_patch = parameter_validation_patch(existing_param, updated_param)

        if unit_patch:
            parameter_patches.append(unit_patch)
        if value_patch:
            parameter_patches.append(value_patch)
        if validation_patch:
            parameter_patches.append(validation_patch)
        if (
            updated_param.validation is not None
            and updated_param.validation != []
            and updated_param.validation[0].datatype == DataType.ENUM
        ):
            existing = (
                existing_param.validation[0].value
                if existing_param.validation is not None and len(existing_param.validation) > 0
                else []
            )
            enum_patches[updated_param.sequence] = generate_enum_patches(
                existing_enums=existing,
                updated_enums=updated_param.validation[0].value,
            )
    return parameter_patches, new_parameters, enum_patches


def handle_tags(
    existing_tags: list[Tag], updated_tags: list[Tag], attribute_name: str = "tag"
) -> list[PatchDatum]:
    """Handle tags updates."""
    patches = []

    existing_tag_ids = [x.id for x in existing_tags] if existing_tags is not None else []
    updated_tag_ids = [x.id for x in updated_tags] if updated_tags is not None else []
    # Add new tags
    for tag in updated_tag_ids:
        if tag not in (existing_tag_ids):
            patches.append(
                PatchDatum(
                    operation="add",
                    attribute=attribute_name,
                    newValue=tag,
                )
            )

    # Remove old tags
    for tag in existing_tag_ids:
        if tag not in (updated_tag_ids):
            patches.append(
                PatchDatum(
                    operation="delete",
                    attribute=attribute_name,
                    oldValue=tag,
                )
            )

    return patches


def generate_data_template_patches(
    initial_patches: PatchPayload,
    updated_data_template: DataTemplate,
    existing_data_template: DataTemplate,
):
    # First handle the data columns
    general_patches = initial_patches
    patches, new_data_columns, data_column_enum_patches = generate_data_column_patches(
        initial_data_column=existing_data_template.data_column_values,
        updated_data_column=updated_data_template.data_column_values,
    )

    tag_patches = handle_tags(
        existing_tags=existing_data_template.tags,
        updated_tags=updated_data_template.tags,
        attribute_name="tag",
    )
    # add the general patches
    general_patches.data.extend(patches)
    general_patches.data.extend(tag_patches)

    parameter_patches, new_parameters, parameter_enum_patches = generate_parameter_patches(
        initial_parameters=existing_data_template.parameter_values,
        updated_parameters=updated_data_template.parameter_values,
        parameter_attribute_name="parameters",
    )

    return (
        general_patches,
        new_data_columns,
        data_column_enum_patches,
        new_parameters,
        parameter_enum_patches,
        parameter_patches,
    )


def generate_parameter_group_patches(
    initial_patches: PatchPayload,
    updated_parameter_group: ParameterGroup,
    existing_parameter_group: ParameterGroup,
):
    # convert to PGPatchPayload to be able to add PGPatchDatum
    general_patches = PGPatchPayload(data=initial_patches.data)
    parameter_patches, new_parameters, parameter_enum_patches = generate_parameter_patches(
        initial_parameters=existing_parameter_group.parameters,
        updated_parameters=updated_parameter_group.parameters,
        parameter_attribute_name="parameter",
    )
    tag_patches = handle_tags(
        existing_tags=existing_parameter_group.tags,
        updated_tags=updated_parameter_group.tags,
        attribute_name="tagId",
    )
    # add to the general patches
    general_patches.data.extend(parameter_patches)
    general_patches.data.extend(tag_patches)

    return general_patches, new_parameters, parameter_enum_patches
