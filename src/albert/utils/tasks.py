from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from albert.collections.attachments import AttachmentCollection
from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DataTemplateId
from albert.core.shared.models.base import EntityLink, EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.resources.data_templates import DataColumnValue
from albert.resources.property_data import TaskDataColumn, TaskPropertyCreate
from albert.resources.tasks import (
    BaseTask,
    PropertyTask,
    TaskInventoryInformation,
    TaskMetadata,
    TaskMetadataBlockdata,
    TaskMetadataDataTemplate,
    TaskMetadataWorkflow,
    TaskPatchPayload,
)

CSV_EXTENSIONS: set[str] = {"csv"}


def build_property_payload(
    *,
    data_rows: Iterable[dict[str, dict]],
    column_to_csv_key: dict[str, str],
    data_columns: Iterable[DataColumnValue],
    interval: str,
    data_template_id: DataTemplateId,
) -> list[TaskPropertyCreate]:
    """Construct TaskPropertyCreate payloads from CSV rows and mapped columns."""
    columns_by_id = {
        column.data_column_id: column
        for column in data_columns
        if column and column.data_column_id
    }

    properties: list[TaskPropertyCreate] = []
    for trial_index, row in enumerate(data_rows, start=1):
        for data_column_id, csv_key in column_to_csv_key.items():
            value = row.get(csv_key)
            if value is None or value == "":
                continue
            column = columns_by_id.get(data_column_id)
            if column is None:
                continue
            properties.append(
                TaskPropertyCreate(
                    data_column=TaskDataColumn(
                        data_column_id=data_column_id,
                        column_sequence=column.sequence,
                    ),
                    value=str(value),
                    visible_trial_number=trial_index,
                    interval_combination=interval,
                    data_template=EntityLink(id=data_template_id),
                )
            )

    return properties


def build_task_metadata(
    *,
    task: PropertyTask,
    block_id: str,
    filename: str | None,
) -> TaskMetadata:
    """Construct task metadata payload for script-driven imports."""

    inventories: list[TaskInventoryInformation] = []
    for inv in task.inventory_information or []:
        inventories.append(
            TaskInventoryInformation(
                inventory_id=inv.inventory_id,
                lot_id=inv.lot_id,
                lot_number=inv.lot_number,
                barcode_id=inv.barcode_id,
            )
        )

    block_info = next((blk for blk in (task.blocks or []) if blk.id == block_id), None)
    if block_info is None:
        raise ValueError(
            f"Block '{block_id}' not found on task {task.id} for metadata construction."
        )
    data_templates: list[TaskMetadataDataTemplate] = []
    for dt in block_info.data_template or []:
        data_templates.append(
            TaskMetadataDataTemplate(
                id=getattr(dt, "id", None) or "",
                name=getattr(dt, "name", None),
                full_name=getattr(dt, "full_name", None),
                standards=getattr(dt, "standards", None),
            )
        )
    workflows: list[TaskMetadataWorkflow] = []
    for wf in block_info.workflow or []:
        workflows.append(
            TaskMetadataWorkflow(
                albert_id=getattr(wf, "id", None),
                name=getattr(wf, "name", None),
            )
        )

    blockdata = TaskMetadataBlockdata(
        id=block_id,
        datatemplate=data_templates,
        workflow=workflows,
    )
    return TaskMetadata(
        filename=filename,
        task_id=task.id,
        block_id=block_id,
        inventories=inventories,
        blockdata=blockdata,
    )


def determine_extension(*, filename: str | None) -> str | None:
    """Return the lowercase extension (without the leading dot) for a filename."""

    if not filename:
        return None
    return Path(filename).suffix.lower().lstrip(".")


def resolve_attachment(
    *,
    attachment_collection: AttachmentCollection,
    task_id: str,
    file_path: str | Path | None,
    attachment_id: str | None,
    allowed_extensions: set[str],
    note_text: str | None,
    upload_key: str | None = None,
) -> str:
    """Ensure an attachment is available, optionally uploading a new file."""
    if file_path is not None:
        path = Path(file_path).expanduser()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found at '{path}'.")
        ext = determine_extension(filename=path.name)
        if allowed_extensions and (ext or "") not in allowed_extensions:
            raise ValueError(
                f"File extension {ext} is not permitted. Allowed extensions: {sorted(allowed_extensions)}"
            )
        note_text_to_use = note_text or ""
        with path.open("rb") as file_handle:
            uploaded_attachment_note = attachment_collection.upload_and_attach_file_as_note(
                parent_id=task_id,
                file_data=file_handle,
                note_text=note_text_to_use,
                file_name=path.name,
                upload_key=upload_key,
            )
        uploaded_attachments = uploaded_attachment_note.attachments or []
        if not uploaded_attachments:
            raise ValueError("Failed to upload attachment. Try again.")
        return uploaded_attachments[0].id

    if attachment_id is None:
        raise ValueError("attachment_id must be provided when file_path is not supplied.")
    return attachment_id


def fetch_csv_table_rows(
    *,
    session: AlbertSession,
    attachment_id: str,
    headers_only: bool = False,
) -> list[dict]:
    """Retrieve the CSV preview rows for a given attachment.

    When ``headers_only`` is True the endpoint returning only the header row is queried.
    """
    endpoint = (
        f"/api/v3/csvtables/{attachment_id}/headers"
        if headers_only
        else f"/api/v3/csvtables/{attachment_id}"
    )
    csv_tables_response = session.get(endpoint)
    csv_tables_payload = csv_tables_response.json()
    if not csv_tables_payload:
        raise ValueError("CSV preview response was empty; unable to import results.")

    first_key = next(iter(csv_tables_payload))
    table_rows = csv_tables_payload[first_key]

    if not isinstance(table_rows, list):
        raise ValueError("CSV preview must contain a header row.")
    return table_rows


def extract_extensions_from_attachment(*, attachment: Any) -> set[str]:
    """Extract allowed file extensions from an attachment's metadata."""

    if attachment is None:
        return set()

    metadata = getattr(attachment, "metadata", None)
    extensions = getattr(metadata, "extensions", None)
    if not extensions:
        return set()

    extracted: set[str] = set()
    for extension in extensions:
        name = getattr(extension, "name", None)
        if isinstance(name, str) and name:
            extracted.add(name.lower().lstrip("."))
    return extracted


def is_metadata_item_list(
    *,
    existing_object: BaseTask,
    updated_object: BaseTask,
    metadata_field: str,
) -> bool:
    """Return True if the metadata field is list-typed on either object."""

    if not metadata_field.startswith("Metadata."):
        return False

    metadata_field = metadata_field.split(".")[1]

    if existing_object.metadata is None:
        existing_object.metadata = {}
    if updated_object.metadata is None:
        updated_object.metadata = {}

    existing = existing_object.metadata.get(metadata_field, None)
    updated = updated_object.metadata.get(metadata_field, None)

    return isinstance(existing, list) or isinstance(updated, list)


def generate_task_patch_payload(
    *,
    collection: BaseCollection,
    existing: BaseTask,
    updated: BaseTask,
) -> TaskPatchPayload:
    """Generate patch payload and capture metadata list updates."""

    base_payload = collection._generate_patch_payload(
        existing=existing,
        updated=updated,
        generate_metadata_diff=True,
    )
    return TaskPatchPayload(data=base_payload.data, id=existing.id)


def generate_adv_patch_payload(
    *,
    collection: BaseCollection,
    updated: BaseTask,
    existing: BaseTask,
) -> TaskPatchPayload:
    """Generate a patch payload for updating a task with special-case fields."""

    _updatable_attributes_special = {
        "inventory_information",
        "assigned_to",
        "tags",
    }
    if updated.assigned_to is not None:
        updated.assigned_to = EntityLinkWithName(
            id=updated.assigned_to.id, name=updated.assigned_to.name
        )
    base_payload = generate_task_patch_payload(
        collection=collection,
        existing=existing,
        updated=updated,
    )

    for attribute in _updatable_attributes_special:
        if attribute == "assigned_to":
            old_value = getattr(existing, attribute)
            new_value = getattr(updated, attribute)
            if new_value == old_value:
                continue
            if new_value and old_value and new_value.id == old_value.id:
                continue
            if old_value is None:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.ADD,
                        "attribute": "AssignedTo",
                        "newValue": new_value,
                    }
                )
                continue

            if new_value is None:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.DELETE,
                        "attribute": "AssignedTo",
                        "oldValue": old_value,
                    }
                )
                continue
            base_payload.data.append(
                {
                    "operation": PatchOperation.UPDATE,
                    "attribute": "AssignedTo",
                    "oldValue": EntityLink(
                        id=old_value.id
                    ),  # can't include name with the old value or you get an error
                    "newValue": new_value,
                }
            )

        if attribute == "inventory_information":
            old_value = getattr(existing, attribute) or []
            new_value = getattr(updated, attribute) or []
            existing_unique = {f"{x.inventory_id}#{x.lot_id}": x for x in old_value}
            updated_unique = {f"{x.inventory_id}#{x.lot_id}": x for x in new_value}

            # Find items to remove (in existing but not in updated)
            inv_to_remove = [
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
                for key, item in existing_unique.items()
                if key not in updated_unique
            ]

            # Find items to add (in updated but not in existing)
            inv_to_add = [
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
                for key, item in updated_unique.items()
                if key not in existing_unique
            ]

            if inv_to_remove:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.DELETE,
                        "attribute": "inventory",
                        "oldValue": inv_to_remove,
                    }
                )

            if inv_to_add:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.ADD,
                        "attribute": "inventory",
                        "newValue": inv_to_add,
                    }
                )

        if attribute == "tags":
            old_value = getattr(existing, attribute) or []
            new_value = getattr(updated, attribute) or []
            existing_tag_ids = {tag.id for tag in old_value if getattr(tag, "id", None)}
            updated_tag_ids = {tag.id for tag in new_value if getattr(tag, "id", None)}

            tags_to_add = updated_tag_ids - existing_tag_ids
            tags_to_remove = existing_tag_ids - updated_tag_ids

            for tag_id in tags_to_add:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.ADD,
                        "attribute": "tagId",
                        "newValue": [tag_id],
                    }
                )

            for tag_id in tags_to_remove:
                base_payload.data.append(
                    {
                        "operation": PatchOperation.DELETE,
                        "attribute": "tagId",
                        "oldValue": [tag_id],
                    }
                )

    return base_payload


def _assign_mapping(
    *,
    identifier: str,
    row_key: str,
    header_name: str,
    column_to_csv_key: dict[str, str],
    used_columns: set[str],
    used_headers: set[str],
) -> None:
    """Register a column-to-CSV mapping and track the consumed identifiers."""

    if not identifier:
        raise ValueError("Column identifier is required to assign mapping.")

    column_to_csv_key[identifier] = row_key
    used_columns.add(identifier)
    used_headers.add(header_name)


def map_csv_headers_to_columns(
    *,
    header_sequence: Iterable[tuple[str, str]],
    data_columns: Iterable[DataColumnValue],
    field_mapping: dict[str, str] | None = None,
    mapping_direction: Literal["csv_to_column", "column_to_csv"] = "csv_to_column",
    use_curve_data_ids: bool = False,
) -> dict[str, str]:
    """Map CSV headers to data template columns using case-insensitive name matches.

    Parameters
    ----------
    header_sequence : Iterable[tuple[str, str]]
        Sequence of tuples pairing row keys (e.g. ``col0``) with header labels.
    data_columns : Iterable[DataColumnValue]
        Iterable of data columns to map against. Hidden columns are ignored.
    field_mapping : dict[str, str] | None
        Optional explicit mappings overriding auto-detection. When ``mapping_direction``
        is ``"csv_to_column"`` (default), keys should match CSV header labels and values should
        match data template column names. When set to ``"column_to_csv"``, provide the inverse:
        keys as data template column names and values as CSV headers.
    mapping_direction : Literal["csv_to_column", "column_to_csv"]
        Direction describing how ``field_mapping`` is interpreted. Defaults to
        ``"csv_to_column"`` for backward compatibility.

    use_curve_data_ids : bool
        When True, map header names against the ``curve_data`` entries attached to each column.
        The resulting mapping keys will be the curve data identifiers rather than the parent
        data column identifiers. Defaults to False.

    Returns
    -------
    dict[str, str]
        Mapping from column identifiers (data column IDs or curve data IDs) to CSV row keys
        (``col#`` values) suitable for payloads.
    """

    visible_columns = [
        column for column in data_columns if column and not getattr(column, "hidden", False)
    ]

    column_to_csv_key: dict[str, str] = {}
    used_columns: set[str] = set()
    used_headers: set[str] = set()

    columns_by_name: dict[str, tuple[str, str]] = {}
    for column in visible_columns:
        if use_curve_data_ids:
            curve_entries = getattr(column, "curve_data", None) or []
            for curve_entry in curve_entries:
                curve_name = getattr(curve_entry, "name", None)
                curve_id = getattr(curve_entry, "id", None)
                if not curve_name or not curve_id:
                    continue
                normalized_name = curve_name.lower()
                if normalized_name in columns_by_name:
                    logger.warning(
                        "Multiple curve data columns share the name '%s'; only the first will be mapped.",
                        curve_name,
                    )
                    continue
                columns_by_name[normalized_name] = (curve_id, curve_name)
        else:
            column_name = column.name
            column_id = getattr(column, "data_column_id", None)
            if not column_name or not column_id:
                continue
            normalized_name = column_name.lower()
            if normalized_name in columns_by_name:
                logger.warning(
                    "Multiple data columns share the name '%s'; only the first will be mapped.",
                    column_name,
                )
                continue
            columns_by_name[normalized_name] = (column_id, column_name)

    header_lookup = {
        header_name.lower(): (row_key, header_name) for row_key, header_name in header_sequence
    }

    mapping = field_mapping or {}
    if mapping and mapping_direction == "column_to_csv":
        mapping = {value: key for key, value in mapping.items()}

    if mapping:
        for csv_header, column_name in mapping.items():
            if not isinstance(csv_header, str) or not isinstance(column_name, str):
                raise ValueError("field_mapping keys and values must be strings.")
            normalized_header = csv_header.lower()
            header_entry = header_lookup.get(normalized_header)
            if header_entry is None:
                logger.warning(
                    "field_mapping entry ignored: CSV header '%s' was not found in the preview.",
                    csv_header,
                )
                continue
            row_key, header_name = header_entry
            normalized_column = column_name.lower()
            matching_entry = columns_by_name.get(normalized_column)
            if matching_entry is None:
                logger.warning(
                    "field_mapping entry ignored: Column '%s' was not found on the template.",
                    column_name,
                )
                continue
            identifier, _display_name = matching_entry
            if identifier in used_columns:
                logger.info(
                    "Column %s already mapped; skipping CSV header '%s'.",
                    identifier,
                    header_name,
                )
                continue
            _assign_mapping(
                identifier=identifier,
                row_key=row_key,
                header_name=header_name,
                column_to_csv_key=column_to_csv_key,
                used_columns=used_columns,
                used_headers=used_headers,
            )

    for row_key, header_name in header_sequence:
        if header_name in used_headers:
            continue
        normalized_header = header_name.lower()
        matching_entry = columns_by_name.get(normalized_header)
        if matching_entry is None:
            logger.info("No matching column found for CSV header '%s'.", header_name)
            continue
        identifier, _display_name = matching_entry
        if identifier in used_columns:
            logger.info(
                "Column %s already mapped; skipping CSV header '%s'.",
                identifier,
                header_name,
            )
            continue
        _assign_mapping(
            identifier=identifier,
            row_key=row_key,
            header_name=header_name,
            column_to_csv_key=column_to_csv_key,
            used_columns=used_columns,
            used_headers=used_headers,
        )

    logger.debug("Resolved column-to-CSV mapping: %s", column_to_csv_key)
    return column_to_csv_key
