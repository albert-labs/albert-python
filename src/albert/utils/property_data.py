"""Utilities for task property data operations."""

from __future__ import annotations

import ast
import math
import mimetypes
import operator
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from albert.collections.attachments import AttachmentCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.files import FileCollection
from albert.core.logging import logger
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import AttachmentId, BlockId, DataTemplateId, TaskId
from albert.core.shared.models.base import EntityLink
from albert.core.shared.models.patch import PatchOperation
from albert.resources.data_templates import CurveDBMetadata, ImportMode, StorageKeyReference
from albert.resources.files import FileNamespace
from albert.resources.property_data import (
    CurvePropertyValue,
    CurvePropertyValuePayload,
    ImagePropertyValue,
    ImagePropertyValuePayload,
    PropertyDataPatchDatum,
    PropertyValue,
    ReturnScope,
    TaskDataColumn,
    TaskPropertyCreate,
    TaskPropertyData,
    TaskPropertyRecord,
    Trial,
)
from albert.resources.tasks import PropertyTask
from albert.resources.workflows import Workflow
from albert.utils.data_template import (
    create_curve_import_job,
    derive_curve_csv_mapping,
    exec_curve_script,
    get_script_attachment,
    get_target_data_column,
    prepare_curve_input_attachment,
    validate_data_column_type,
)
from albert.utils.tasks import CSV_EXTENSIONS, fetch_csv_table_rows


def get_task_from_id(*, session: AlbertSession, id: TaskId) -> PropertyTask:
    """Fetch a PropertyTask by id using the task collection."""
    from albert.collections.tasks import TaskCollection

    return TaskCollection(session=session).get_by_id(id=id)


def resolve_return_scope(
    *,
    task_id: TaskId,
    return_scope: ReturnScope,
    inventory_id,
    block_id,
    lot_id,
    prefetched_block: TaskPropertyData | None,
    get_all_task_properties: Callable[..., list[TaskPropertyData]],
    get_task_block_properties: Callable[..., TaskPropertyData],
) -> list[TaskPropertyData]:
    """Resolve the return payload based on scope and cached block data."""
    if return_scope == "task":
        return get_all_task_properties(task_id=task_id)

    if return_scope == "block":
        if prefetched_block is not None:
            return [prefetched_block]
        if inventory_id is None or block_id is None:
            raise ValueError("inventory_id and block_id are required when return_scope='block'.")
        return [
            get_task_block_properties(
                inventory_id=inventory_id,
                task_id=task_id,
                block_id=block_id,
                lot_id=lot_id,
            )
        ]

    return []


def resolve_image_property_value(
    *, session: AlbertSession, task_id: TaskId, image_value: ImagePropertyValue
) -> dict:
    """Upload an image file and return the resolved payload dict."""
    resolved_path = Path(image_value.file_path).expanduser()
    if not resolved_path.exists() or not resolved_path.is_file():
        raise FileNotFoundError(f"File not found at '{resolved_path}'.")
    upload_ext = resolved_path.suffix.lower()
    if not upload_ext:
        raise ValueError("File extension is required for image property data.")

    upload_key = f"imagedata/original/{task_id}/{uuid.uuid4().hex[:10]}{upload_ext}"
    file_name = resolved_path.name
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_collection = FileCollection(session=session)
    with resolved_path.open("rb") as file_handle:
        file_collection.sign_and_upload_file(
            data=file_handle,
            name=upload_key,
            namespace=FileNamespace.RESULT,
            content_type=content_type,
        )

    value = ImagePropertyValuePayload(
        file_name=file_name,
        s3_key=StorageKeyReference(
            original=upload_key,
            thumb=upload_key,
            preview=upload_key,
        ),
    )
    return value.model_dump(by_alias=True, mode="json", exclude_none=True)


def resolve_curve_property_value(
    *,
    session: AlbertSession,
    task_id: TaskId,
    block_id: BlockId | None,
    prop: TaskPropertyCreate,
    curve_value: CurvePropertyValue,
) -> dict:
    """Upload/import curve data and return the resolved payload dict."""
    if block_id is None:
        raise ValueError("block_id is required to import curve data for task properties.")

    data_template_id = resolve_data_template_id(prop=prop)
    data_template = DataTemplateCollection(session=session).get_by_id(id=data_template_id)
    target_column = get_target_data_column(
        data_template=data_template,
        data_template_id=data_template_id,
        data_column_id=prop.data_column.data_column_id,
        data_column_name=None,
    )
    validate_data_column_type(target_column=target_column)
    column_id = target_column.data_column_id
    if column_id is None:
        raise ValueError("Curve data column is missing an identifier.")

    attachment_collection = AttachmentCollection(session=session)
    file_collection = FileCollection(session=session)

    script_attachment_signed_url: str | None = None
    if curve_value.mode is ImportMode.SCRIPT:
        script_attachment, script_extensions = get_script_attachment(
            attachment_collection=attachment_collection,
            data_template_id=data_template_id,
            column_id=column_id,
        )
        if not script_extensions:
            raise ValueError("Script attachment must define allowed extensions.")
        script_attachment_signed_url = script_attachment.signed_url
        allowed_extensions = set(script_extensions)
    else:
        allowed_extensions = set(CSV_EXTENSIONS)

    upload_key = (
        f"curve-input/{task_id}/{block_id}/{data_template_id}/"
        f"{column_id}/{uuid.uuid4().hex[:10]}.csv"
    )
    raw_attachment = prepare_curve_input_attachment(
        attachment_collection=attachment_collection,
        data_template_id=data_template_id,
        column_id=column_id,
        allowed_extensions=allowed_extensions,
        file_path=curve_value.file_path,
        attachment_id=None,
        require_signed_url=curve_value.mode is ImportMode.SCRIPT,
        parent_id=task_id,
        upload_key=upload_key,
    )

    raw_key = raw_attachment.key
    if not raw_key:
        raise ValueError("Curve input attachment does not include an S3 key.")
    if raw_attachment.id is None:
        raise ValueError("Curve input attachment did not return an identifier.")
    resolved_attachment_id = AttachmentId(raw_attachment.id)

    processed_input_key = raw_key
    column_headers: dict[str, str] = {}

    if curve_value.mode is ImportMode.SCRIPT:
        processed_input_key, column_headers = exec_curve_script(
            session=session,
            data_template_id=data_template_id,
            column_id=column_id,
            raw_attachment=raw_attachment,
            file_collection=file_collection,
            script_attachment_signed_url=script_attachment_signed_url,
            task_id=task_id,
            block_id=block_id,
        )
    else:
        table_rows = fetch_csv_table_rows(
            session=session,
            attachment_id=resolved_attachment_id,
            headers_only=True,
        )
        header_row = table_rows[0]
        if not isinstance(header_row, dict):
            raise ValueError("Unexpected CSV header format returned by preview endpoint.")
        column_headers = {
            key: value
            for key, value in header_row.items()
            if isinstance(key, str) and isinstance(value, str) and value
        }

    csv_mapping = derive_curve_csv_mapping(
        target_column=target_column,
        column_headers=column_headers,
        field_mapping=curve_value.field_mapping,
    )

    job_id, partition_uuid, s3_output_key = create_curve_import_job(
        session=session,
        data_template_id=data_template_id,
        column_id=column_id,
        csv_mapping=csv_mapping,
        raw_attachment=raw_attachment,
        processed_input_key=processed_input_key,
        task_id=task_id,
        block_id=block_id,
    )

    table_name = f"{str(data_template_id).lower()}_{str(column_id).lower()}"
    value = CurvePropertyValuePayload(
        file_name=raw_attachment.name or "",
        s3_key=StorageKeyReference(
            s3_input=processed_input_key,
            rawfile=processed_input_key,
            s3_output=s3_output_key,
        ),
        job_id=job_id,
        csv_mapping=csv_mapping,
        athena=CurveDBMetadata(
            table_name=table_name,
            partition_key=partition_uuid,
        ),
    )
    return value.model_dump(by_alias=True, mode="json", exclude_none=True)


def resolve_data_template_id(*, prop: TaskPropertyCreate) -> DataTemplateId:
    """Extract the data template id from a task property."""
    data_template = prop.data_template
    data_template_id = getattr(data_template, "id", None)
    if data_template_id is None and isinstance(data_template, dict):
        data_template_id = data_template.get("id") or data_template.get("albertId")
    if data_template_id is None:
        raise ValueError("data_template is required to import curve data.")
    return data_template_id


def resolve_task_property_payload(
    *,
    session: AlbertSession,
    task_id: TaskId,
    block_id: BlockId | None,
    properties: list[TaskPropertyCreate],
) -> list[dict]:
    """Build POST payloads for task properties, resolving image/curve values."""
    has_curve = any(isinstance(prop.value, CurvePropertyValue) for prop in properties)
    payload = []
    for prop in properties:
        prop_payload = prop.model_dump(exclude_none=True, by_alias=True, mode="json")
        if isinstance(prop.value, ImagePropertyValue):
            prop_payload["value"] = resolve_image_property_value(
                session=session,
                task_id=task_id,
                image_value=prop.value,
            )
        elif isinstance(prop.value, CurvePropertyValue):
            prop_payload["value"] = resolve_curve_property_value(
                session=session,
                task_id=task_id,
                block_id=block_id,
                prop=prop,
                curve_value=prop.value,
            )
        # When any curve property is in the batch, the backend evaluates the array
        # against CurveData (which has additionalProperties: false and does not define DataTemplate).
        # DataTemplate must therefore be stripped from every item in the batch.
        if has_curve:
            prop_payload.pop("DataTemplate", None)
        payload.append(prop_payload)
    return payload


def resolve_patch_payload(
    *,
    session: AlbertSession,
    task_id: TaskId,
    patch_payload: list[PropertyDataPatchDatum],
) -> list[dict]:
    """Build PATCH payloads."""
    resolved_payload = []
    for patch in patch_payload:
        if isinstance(patch.new_value, ImagePropertyValue | CurvePropertyValue):
            raise ValueError(
                "Update ImagePropertyValue and CurvePropertyValue via "
                "update_or_create_task_properties."
            )
        resolved_payload.append(patch.model_dump(exclude_none=True, by_alias=True, mode="json"))
    return resolved_payload


def _get_column_map(
    *, dataframe: pd.DataFrame, property_data: TaskPropertyData
) -> dict[str, PropertyValue]:
    """Map dataframe columns to property data columns for bulk loads."""
    data_col_info = property_data.data[0].trials[0].data_columns
    column_map: dict[str, PropertyValue] = {}
    for col in dataframe.columns:
        column = [x for x in data_col_info if x.name == col]
        if len(column) == 1:
            column_map[col] = column[0]
        else:
            raise ValueError(
                f"Column '{col}' not found in block data columns or multiple matches found."
            )
    return column_map


def _df_to_task_prop_create_list(
    *,
    dataframe: pd.DataFrame,
    column_map: dict[str, PropertyValue],
    data_template_id: DataTemplateId,
    interval: str,
) -> list[TaskPropertyCreate]:
    """Convert a dataframe into TaskPropertyCreate entries."""
    task_prop_create_list: list[TaskPropertyCreate] = []
    for i, row in dataframe.iterrows():
        for col_name, col_info in column_map.items():
            if col_name not in dataframe.columns:
                raise ValueError(f"Column '{col_name}' not found in DataFrame.")

            task_prop_create_list.append(
                TaskPropertyCreate(
                    data_column=TaskDataColumn(
                        data_column_id=col_info.id,
                        column_sequence=col_info.sequence,
                    ),
                    value=str(row[col_name]),
                    visible_trial_number=i + 1,
                    interval_combination=interval,
                    data_template=EntityLink(id=data_template_id),
                )
            )
    return task_prop_create_list


def form_existing_row_value_patches(
    *,
    session: AlbertSession,
    task_id: TaskId,
    block_id: BlockId,
    existing_data_rows: TaskPropertyData,
    properties: list[TaskPropertyCreate],
):
    """Split incoming properties into patches vs new rows."""
    patches = []
    new_properties = []

    for prop in properties:
        resolved_trial_number = resolve_trial_number(
            prop=prop,
            existing_data_rows=existing_data_rows,
        )
        if resolved_trial_number is None:
            new_properties.append(prop)
            continue

        prop_patches = process_property(
            session=session,
            task_id=task_id,
            block_id=block_id,
            prop=prop,
            existing_data_rows=existing_data_rows,
            trial_number=resolved_trial_number,
        )
        if prop_patches is not None:
            if prop_patches:
                patches.extend(prop_patches)
            continue
        new_properties.append(
            prepare_new_task_property(
                prop=prop,
                existing_data_rows=existing_data_rows,
                trial_number=resolved_trial_number,
            )
        )

    return patches, new_properties


def trial_has_recorded_data(
    *,
    existing_data_rows: TaskPropertyData,
    interval_combination: str,
    trial_number: int,
) -> bool:
    """Return True if the trial already has at least one stored property-data value."""
    trial = get_on_platform_row(
        existing_data_rows=existing_data_rows,
        interval_combination=interval_combination,
        trial_number=trial_number,
    )
    if trial is None:
        return False
    return any(col.property_data is not None for col in trial.data_columns)


def prepare_new_task_property(
    *,
    prop: TaskPropertyCreate,
    existing_data_rows: TaskPropertyData,
    trial_number: int | None,
) -> TaskPropertyCreate:
    """Keep trial_number only when it refers to a trial that already has stored data.

    A block listing can include an empty placeholder trial. That placeholder is
    not a stored trial, so trial_number is omitted and a new trial is created.
    If the trial already has data, trial_number is kept so a missing column is
    added to that trial.
    """
    if trial_number is None:
        return prop
    if trial_has_recorded_data(
        existing_data_rows=existing_data_rows,
        interval_combination=prop.interval_combination,
        trial_number=trial_number,
    ):
        if prop.trial_number == trial_number:
            return prop
        return prop.model_copy(update={"trial_number": trial_number})
    if prop.trial_number is None:
        return prop
    return prop.model_copy(update={"trial_number": None})


def process_property(
    *,
    session: AlbertSession,
    task_id: TaskId,
    block_id: BlockId,
    prop: TaskPropertyCreate,
    existing_data_rows: TaskPropertyData,
    trial_number: int,
) -> list | None:
    """Resolve patches for a property against existing trials."""
    for interval in existing_data_rows.data:
        if interval.interval_combination != prop.interval_combination:
            continue

        for trial in interval.trials:
            if trial.trial_number != trial_number:
                continue

            trial_patches = process_trial(
                session=session,
                task_id=task_id,
                block_id=block_id,
                trial=trial,
                prop=prop,
            )
            if trial_patches is not None:
                return trial_patches

    return None


def resolve_trial_number(
    *, prop: TaskPropertyCreate, existing_data_rows: TaskPropertyData
) -> int | None:
    """Resolve the trial number for a property using visible trial numbers."""
    if prop.trial_number is not None:
        return prop.trial_number

    visible_trial_number = prop.visible_trial_number
    if visible_trial_number is None:
        return None
    if isinstance(visible_trial_number, str):
        try:
            visible_trial_number = int(visible_trial_number)
        except ValueError:
            return None

    matching_trials = []
    for interval in existing_data_rows.data:
        if interval.interval_combination != prop.interval_combination:
            continue
        for trial in interval.trials:
            if trial.visible_trial_number == visible_trial_number:
                matching_trials.append(trial.trial_number)

    if len(matching_trials) == 1:
        return matching_trials[0]
    return None


def process_trial(
    *,
    session: AlbertSession,
    task_id: TaskId,
    block_id: BlockId,
    trial: Trial,
    prop: TaskPropertyCreate,
) -> list | None:
    """Generate patch operations for a trial's matching data column."""
    for data_column in trial.data_columns:
        if (
            data_column.data_column_unique_id
            == f"{prop.data_column.data_column_id}#{prop.data_column.column_sequence}"
            and data_column.property_data is not None
        ):
            if isinstance(prop.value, CurvePropertyValue):
                resolved_value = resolve_curve_property_value(
                    session=session,
                    task_id=task_id,
                    block_id=block_id,
                    prop=prop,
                    curve_value=prop.value,
                )
                return [
                    PropertyDataPatchDatum(
                        id=data_column.property_data.id,
                        operation=PatchOperation.UPDATE,
                        attribute="value",
                        new_value=resolved_value,
                        old_value=data_column.property_data.value,
                    )
                ]
            if isinstance(prop.value, ImagePropertyValue):
                resolved_value = resolve_image_property_value(
                    session=session,
                    task_id=task_id,
                    image_value=prop.value,
                )
                return [
                    PropertyDataPatchDatum(
                        id=data_column.property_data.id,
                        operation=PatchOperation.UPDATE,
                        attribute="value",
                        new_value=resolved_value,
                        old_value=data_column.property_data.value,
                    )
                ]
            if data_column.property_data.value == prop.value:
                return []
            return [
                PropertyDataPatchDatum(
                    id=data_column.property_data.id,
                    operation=PatchOperation.UPDATE,
                    attribute="value",
                    new_value=prop.value,
                    old_value=data_column.property_data.value,
                )
            ]

    return None


def form_calculated_task_property_patches(
    *, existing_data_rows: TaskPropertyData, properties: list[TaskPropertyCreate]
):
    """Build patches for calculated columns after property updates."""
    patches = []
    covered_interval_trials = set()
    first_row_data_column = existing_data_rows.data[0].trials[0].data_columns
    columns_used_in_calculations = get_all_columns_used_in_calculations(
        first_row_data_column=first_row_data_column
    )
    for posted_prop in properties:
        trial_number = posted_prop.trial_number
        if trial_number is None:
            trial_number = resolve_trial_number(
                prop=posted_prop,
                existing_data_rows=existing_data_rows,
            )
        if trial_number is None:
            continue
        this_interval_trial = f"{posted_prop.interval_combination}-{trial_number}"
        if (
            this_interval_trial in covered_interval_trials
            or posted_prop.data_column.column_sequence not in columns_used_in_calculations
        ):
            continue
        on_platform_row = get_on_platform_row(
            existing_data_rows=existing_data_rows,
            trial_number=trial_number,
            interval_combination=posted_prop.interval_combination,
        )
        if on_platform_row is not None:
            these_patches = generate_data_patch_payload(trial=on_platform_row)
            patches.extend(these_patches)
        covered_interval_trials.add(this_interval_trial)
    return patches


def get_on_platform_row(
    *, existing_data_rows: TaskPropertyData, interval_combination: str, trial_number: int
):
    """Find the matching trial row by interval and trial number."""
    for interval in existing_data_rows.data:
        if interval.interval_combination == interval_combination:
            for trial in interval.trials:
                if trial.trial_number == trial_number:
                    return trial
    return None


def get_columns_used_in_calculation(*, calculation: str | None, used_columns: set[str]):
    """Collect column identifiers referenced in a calculation string."""
    if calculation is None:
        return used_columns
    column_pattern = r"COL\d+"
    matches = re.findall(column_pattern, calculation)
    used_columns.update(set(matches))
    return used_columns


def get_all_columns_used_in_calculations(*, first_row_data_column: list):
    """Aggregate column identifiers used in calculation fields."""
    used_columns = set()
    for calc in [x.calculation for x in first_row_data_column]:
        used_columns = get_columns_used_in_calculation(calculation=calc, used_columns=used_columns)
    return used_columns


_MAX_POW_RESULT_BITS = 100_000


def _safe_pow(base: float, exponent: float) -> float:
    """Raise ``base`` to ``exponent``, rejecting integer results too large to compute quickly."""
    if (
        isinstance(base, int)
        and isinstance(exponent, int)
        and exponent > 0
        and base.bit_length() * exponent > _MAX_POW_RESULT_BITS
        and abs(base) > 1
    ):
        raise ValueError("Exponentiation result is too large.")
    return operator.pow(base, exponent)


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: _safe_pow,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_ALLOWED_FUNCS: dict[str, tuple[Callable[..., float], int]] = {
    "log10": (math.log10, 1),
    "ln": (math.log, 1),
    "sqrt": (math.sqrt, 1),
    "pi": (lambda: math.pi, 0),
}
_ALLOWED_NAMES = {"pi": math.pi}


def _safe_eval_math(*, expression: str) -> float:
    """Safely evaluate supported math expressions."""
    parsed = ast.parse(expression, mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int | float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
            return _ALLOWED_UNARYOPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Unsupported function call.")
            func_name = node.func.id
            if func_name not in _ALLOWED_FUNCS:
                raise ValueError("Unsupported function.")
            if node.keywords:
                raise ValueError("Keyword arguments are not supported.")
            func, arity = _ALLOWED_FUNCS[func_name]
            if len(node.args) != arity:
                raise ValueError("Unsupported function arity.")
            if arity == 0:
                return func()
            return func(_eval(node.args[0]))
        if isinstance(node, ast.Name):
            if node.id in _ALLOWED_NAMES:
                return _ALLOWED_NAMES[node.id]
            raise ValueError("Unsupported name.")
        raise ValueError("Unsupported expression.")

    return _eval(parsed)


def evaluate_calculation(*, calculation: str, column_values: dict) -> float | None:
    """Evaluate a calculation expression against column values."""
    calculation = calculation.lstrip("=")
    try:
        if column_values:
            escaped_cols = [re.escape(col) for col in column_values]
            pattern = re.compile(rf"\b({'|'.join(escaped_cols)})\b")

            def repl(match: re.Match) -> str:
                """Replace column tokens with values in a calculation expression."""
                col = match.group(0)
                return str(column_values.get(col, match.group(0)))

            calculation = pattern.sub(repl, calculation)

        calculation = calculation.replace("^", "**")
        return _safe_eval_math(expression=calculation)
    except Exception as e:
        logger.info(
            "Error evaluating calculation '%s': %s. Likely do not have all values needed.",
            calculation,
            e,
        )
        return None


def generate_data_patch_payload(*, trial: Trial) -> list[PropertyDataPatchDatum]:
    """Generate patch payloads for calculated columns in a trial."""
    column_values = {
        col.sequence: col.property_data.value
        for col in trial.data_columns
        if col.property_data is not None
    }

    patch_data = []
    for column in trial.data_columns:
        if column.calculation and column.property_data is not None:
            recalculated_value = evaluate_calculation(
                calculation=column.calculation, column_values=column_values
            )
            if recalculated_value is not None:
                if column.property_data.value is None:
                    patch_data.append(
                        PropertyDataPatchDatum(
                            id=column.property_data.id,
                            operation=PatchOperation.ADD,
                            attribute="value",
                            new_value=recalculated_value,
                            old_value=None,
                        )
                    )
                elif str(column.property_data.value) != str(recalculated_value):
                    patch_data.append(
                        PropertyDataPatchDatum(
                            id=column.property_data.id,
                            operation=PatchOperation.UPDATE,
                            attribute="value",
                            new_value=recalculated_value,
                            old_value=column.property_data.value,
                        )
                    )

    return patch_data


def _setpoint_display_value(value: Any) -> str | None:
    """Reduce a setpoint or interval value to a plain string for tabular output."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        return str(value.get("name") or value.get("id") or value)
    return getattr(value, "name", None) or getattr(value, "id", None) or str(value)


def build_interval_setpoint_map(*, workflow: Workflow) -> dict[str, dict[str, str]]:
    """Map each interval ID of a workflow to the parameter setpoints it represents.

    Combines the parameters the interval varies with the workflow's fixed setpoints, so
    each entry is the complete set of conditions for that interval. The ``"default"``
    key holds the fixed setpoints alone, for blocks with no intervalized parameters.

    Only ROW-chain interval IDs are resolved. Tenants running the increased-intervals
    beta address data by child workflow ID instead, and those IDs do not correspond to
    the workflow's own interval rows, so they are left out.

    Parameters
    ----------
    workflow : Workflow
        A fully populated workflow, as returned by
        [`get_by_id`][albert.collections.workflows.WorkflowCollection.get_by_id].

    Returns
    -------
    dict[str, dict[str, str]]
        Interval ID to a mapping of parameter name to value.
    """
    fixed: dict[str, str] = {}
    varied: dict[str, tuple[str, str]] = {}

    for group in workflow.parameter_group_setpoints or []:
        for setpoint in group.parameter_setpoints or []:
            name = setpoint.name or setpoint.short_name or setpoint.parameter_id
            if not name:
                continue
            if setpoint.intervals:
                for interval in setpoint.intervals:
                    if interval.row_id:
                        value = _setpoint_display_value(interval.value)
                        varied[interval.row_id] = (name, "" if value is None else value)
            else:
                value = _setpoint_display_value(setpoint.value)
                if value is not None:
                    fixed[name] = value

    interval_map: dict[str, dict[str, str]] = {"default": dict(fixed)}

    # An interval ID is a chain of the row IDs of each varied parameter, joined with "X".
    interval_ids = {c.interval_id for c in (workflow.interval_combinations or []) if c.interval_id}
    interval_ids.update(varied)
    for interval_id in interval_ids:
        setpoints = dict(fixed)
        resolved = True
        for row_id in interval_id.split("X"):
            if row_id not in varied:
                resolved = False
                break
            name, value = varied[row_id]
            setpoints[name] = value
        if resolved:
            interval_map[interval_id] = setpoints

    return interval_map


def map_block_final_workflows(*, task: PropertyTask) -> dict[str, Workflow | EntityLink]:
    """Map each block ID of a task to that block's FINAL workflow.

    The property data endpoints do not return the workflows, so the block is the only
    place to learn which workflow's setpoints apply to a block's results.
    """
    mapping: dict[str, Workflow | EntityLink] = {}
    for block in getattr(task, "blocks", None) or []:
        workflow = getattr(block, "workflow", None)
        candidates = workflow if isinstance(workflow, list) else [workflow]
        chosen = None
        for candidate in candidates:
            if candidate is None:
                continue
            if str(getattr(candidate, "category", "") or "").upper() == "FINAL":
                chosen = candidate
                break
            chosen = chosen or candidate
        if chosen is not None:
            mapping[block.id] = chosen
    return mapping


def flatten_task_property_data(
    *,
    block: TaskPropertyData,
    task_id: TaskId,
    workflow_id: str | None,
    workflow_name: str | None,
    interval_setpoints: dict[str, dict[str, str]],
    interval_descriptions: dict[str, str],
) -> list[TaskPropertyRecord]:
    """Flatten one block's interval/trial tree into one record per measured value."""
    data_template = block.data_template
    inventory = block.inventory

    records: list[TaskPropertyRecord] = []
    for interval in block.data:
        interval_id = interval.interval_combination
        setpoints = interval_setpoints.get(interval_id, {})
        description = interval_descriptions.get(interval_id) or interval.name
        for trial in interval.trials:
            for column in trial.data_columns:
                property_data = column.property_data
                unit = column.unit
                unit_name = (
                    unit.get("name") if isinstance(unit, dict) else getattr(unit, "name", None)
                )
                records.append(
                    TaskPropertyRecord(
                        task_id=task_id,
                        block_id=block.block_id,
                        data_template_id=getattr(data_template, "id", None),
                        data_template_name=getattr(data_template, "name", None),
                        inventory_id=getattr(inventory, "inventory_id", None),
                        lot_id=getattr(inventory, "lot_id", None),
                        interval_combination=interval_id,
                        interval_description=description.strip() if description else None,
                        parameter_setpoints=dict(setpoints),
                        trial_number=trial.trial_number,
                        visible_trial_number=trial.visible_trial_number,
                        void=interval.void or trial.void,
                        data_column_id=column.id,
                        data_column_name=column.name,
                        sequence=column.sequence,
                        property_data_id=getattr(property_data, "id", None),
                        value=column.value
                        if column.value is not None
                        else getattr(property_data, "value", None),
                        numeric_value=column.numeric_value,
                        unit_name=unit_name,
                        calculation=column.calculation,
                        workflow_id=workflow_id,
                        workflow_name=workflow_name,
                    )
                )
    return records
