from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from albert.collections.attachments import AttachmentCollection
from albert.core.logging import logger
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DataTemplateId
from albert.core.shared.models.base import EntityLink
from albert.resources.data_templates import DataColumnValue
from albert.resources.property_data import TaskDataColumn, TaskPropertyCreate
from albert.resources.tasks import (
    PropertyTask,
    TaskInventoryInformation,
    TaskMetadata,
    TaskMetadataBlockdata,
    TaskMetadataDataTemplate,
    TaskMetadataWorkflow,
)


def determine_extension(*, filename: str | None) -> str | None:
    """Return the lowercase extension (without the leading dot) for a filename."""

    if not filename:
        return None
    return Path(filename).suffix.lower().lstrip(".")


def assign_mapping(
    *,
    column: DataColumnValue,
    row_key: str,
    header_name: str,
    column_to_csv_key: dict[str, str],
    used_columns: set[str],
    used_headers: set[str],
) -> None:
    """Register a column-to-CSV mapping and track the consumed identifiers."""

    if not column.data_column_id:
        raise ValueError("Data column must define 'data_column_id' to assign mapping.")

    column_to_csv_key[column.data_column_id] = row_key
    used_columns.add(column.data_column_id)
    used_headers.add(header_name)


def extract_extensions_from_attachment(*, attachment) -> set[str]:
    """Extract allowed file extensions from an attachment's metadata."""

    if attachment is None:
        return set()

    metadata = getattr(attachment, "metadata", None)
    extensions = getattr(metadata, "extensions", None)
    if not extensions:
        return set()

    return {ext.name.lower().lstrip(".") for ext in extensions if getattr(ext, "name", None)}


def map_csv_headers_to_columns(
    *,
    header_sequence: Iterable[tuple[str, str]],
    data_columns: Iterable[DataColumnValue],
    field_mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Map CSV headers to data template columns using case-insensitive name matches."""

    visible_columns = [
        column for column in data_columns if column and not getattr(column, "hidden", False)
    ]

    column_to_csv_key: dict[str, str] = {}
    used_columns: set[str] = set()
    used_headers: set[str] = set()

    columns_by_name: dict[str, DataColumnValue] = {}
    for column in visible_columns:
        column_name = column.name
        if not column_name or not column.data_column_id:
            continue
        normalized_name = column_name.lower()
        if normalized_name in columns_by_name:
            logger.warning(
                "Multiple data columns share the name '%s'; only the first will be mapped.",
                column_name,
            )
            continue
        columns_by_name[normalized_name] = column

    header_lookup = {
        header_name.lower(): (row_key, header_name) for row_key, header_name in header_sequence
    }

    if field_mapping:
        for csv_header, column_name in field_mapping.items():
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
            matching_column = columns_by_name.get(normalized_column)
            if matching_column is None:
                logger.warning(
                    "field_mapping entry ignored: Data column '%s' was not found on the template.",
                    column_name,
                )
                continue
            if matching_column.data_column_id in used_columns:
                logger.warning(
                    "Data column %s already mapped; skipping CSV header '%s'.",
                    matching_column.data_column_id,
                    header_name,
                )
                continue
            assign_mapping(
                column=matching_column,
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
        matching_column = columns_by_name.get(normalized_header)
        if matching_column is None:
            logger.warning("No matching data column found for CSV header '%s'.", header_name)
            continue
        if matching_column.data_column_id in used_columns:
            logger.warning(
                "Data column %s already mapped; skipping CSV header '%s'.",
                matching_column.data_column_id,
                header_name,
            )
            continue
        assign_mapping(
            column=matching_column,
            row_key=row_key,
            header_name=header_name,
            column_to_csv_key=column_to_csv_key,
            used_columns=used_columns,
            used_headers=used_headers,
        )

    logger.debug("Resolved column-to-CSV mapping: %s", column_to_csv_key)
    return column_to_csv_key


def build_property_payload(
    *,
    data_rows: Iterable[dict[str, object]],
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


def resolve_attachment(
    *,
    attachment_collection: AttachmentCollection,
    task_id: str,
    file_path: str | Path | None,
    attachment_id: str | None,
    allowed_extensions: set[str],
    note_text: str | None,
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
    api_version: str,
    attachment_id: str,
    csv_table_key: str | None,
) -> list[object]:
    """Retrieve the CSV preview rows for a given attachment."""

    csv_tables_response = session.get(f"/api/{api_version}/csvtables/{attachment_id}")
    csv_tables_payload = csv_tables_response.json()
    if not csv_tables_payload:
        raise ValueError("CSV preview response was empty; unable to import results.")

    if csv_table_key:
        if csv_table_key not in csv_tables_payload:
            raise ValueError(f"CSV table key '{csv_table_key}' not found in preview response.")
        table_rows = csv_tables_payload[csv_table_key]
    else:
        first_key = next(iter(csv_tables_payload))
        table_rows = csv_tables_payload[first_key]

    if not isinstance(table_rows, list) or len(table_rows) < 2:
        raise ValueError(
            "CSV preview must contain a header row followed by at least one data row."
        )

    return table_rows
