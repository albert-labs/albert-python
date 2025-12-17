"""Utilities for working with data templates."""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from tenacity import retry, stop_after_attempt, wait_exponential

from albert.core.logging import logger
from albert.core.shared.identifiers import AttachmentId, DataColumnId, DataTemplateId
from albert.core.shared.models.patch import (
    GeneralPatchDatum,
    GeneralPatchPayload,
    PatchOperation,
    PGPatchDatum,
)
from albert.exceptions import AlbertHTTPError
from albert.resources.attachments import Attachment, AttachmentCategory
from albert.resources.data_templates import DataColumnValue, DataTemplate
from albert.resources.files import FileNamespace
from albert.resources.parameter_groups import DataType, ValueValidation
from albert.resources.tasks import CsvCurveInput, CsvCurveResponse, TaskMetadata
from albert.resources.worker_jobs import (
    WORKER_JOB_PENDING_STATES,
    WorkerJob,
    WorkerJobCreateRequest,
    WorkerJobMetadata,
    WorkerJobState,
)
from albert.utils.tasks import (
    determine_extension,
    extract_extensions_from_attachment,
    map_csv_headers_to_columns,
    resolve_attachment,
)

if TYPE_CHECKING:
    from albert.collections.attachments import AttachmentCollection
    from albert.collections.files import FileCollection
    from albert.core.session import AlbertSession


_CURVE_JOB_POLL_INTERVAL = 2.0
_CURVE_JOB_MAX_ATTEMPTS = 20
_CURVE_JOB_MAX_WAIT = 10.0


def get_target_data_column(
    *,
    data_template: DataTemplate,
    data_template_id: DataTemplateId,
    data_column_id: DataColumnId | None,
    data_column_name: str | None,
) -> DataColumnValue:
    """Resolve a data template column by id or name and return the matched entry.

    Raises
    ------
    ValueError
        If neither or both identifiers are provided, if the data template has no columns,
        or if the matching column cannot be found.
    """
    if (data_column_id is None) == (data_column_name is None):
        raise ValueError("Provide exactly one of 'data_column_id' or 'data_column_name'.")

    data_columns = data_template.data_column_values or []
    if not data_columns:
        raise ValueError(
            f"Data template {data_template_id} does not define any data columns to import."
        )

    if data_column_id is not None:
        target_column = next(
            (col for col in data_columns if col.data_column_id == data_column_id),
            None,
        )
    else:
        lowered_name = data_column_name.lower()
        target_column = next(
            (
                col
                for col in data_columns
                if isinstance(col.name, str) and col.name.lower() == lowered_name
            ),
            None,
        )

    if target_column is None:
        identifier = data_column_id or data_column_name
        raise ValueError(f"Data column '{identifier}' was not found on the template.")

    return target_column


def validate_data_column_type(*, target_column: DataColumnValue) -> None:
    """Ensure the resolved data column is configured for curve data."""

    validations = target_column.validation or []
    if not any(_validation_is_curve(validation) for validation in validations):
        raise ValueError(
            f"Data column '{target_column.name}' must be a curve-type column to import curve data."
        )


def get_script_attachment(
    *,
    attachment_collection: "AttachmentCollection",
    data_template_id: DataTemplateId,
    column_id: DataColumnId,
) -> tuple[Attachment, set[str]]:
    """Fetch the script attachment for a data column and return it with allowed extensions."""

    try:
        parent_map = attachment_collection.get_by_parent_ids(
            parent_ids=[data_template_id], data_column_ids=[column_id]
        )
    except AlbertHTTPError as exc:
        if getattr(exc.response, "status_code", None) == 404:
            raise ValueError(
                f"Script import requested but no script attached to the data column '{column_id}'."
            ) from exc
        raise

    script_candidates = parent_map.get(data_template_id, []) if parent_map else []
    if not script_candidates:
        raise ValueError(
            "Script import requested but no active script attachment was found on the data template or data column."
        )
    script_attachment = script_candidates[0]
    if script_attachment.category != AttachmentCategory.SCRIPT:
        raise ValueError(
            f"Script import requested but the attachment on data column '{column_id}' is not a script."
        )

    if not getattr(script_attachment, "signed_url", None):
        raise ValueError(
            "Script import requested but no active script attachment with a signed URL was found on the data template or data column."
        )

    allowed_extensions = extract_extensions_from_attachment(attachment=script_attachment)

    return script_attachment, allowed_extensions


def prepare_curve_input_attachment(
    *,
    attachment_collection: "AttachmentCollection",
    data_template_id: DataTemplateId,
    column_id: DataColumnId,
    allowed_extensions: set[str] | None,
    file_path: str | Path | None,
    attachment_id: AttachmentId | None,
    require_signed_url: bool,
) -> Attachment:
    """Resolve the input attachment, uploading a file when required, and validate it."""

    if (attachment_id is None) == (file_path is None):
        raise ValueError("Provide exactly one of 'attachment_id' or 'file_path'.")

    allowed_extensions = set(allowed_extensions or ())
    normalized_extensions = {ext.lower().lstrip(".") for ext in allowed_extensions if ext}
    display_extensions = sorted(allowed_extensions) if allowed_extensions else []

    upload_key: str | None = None
    resolved_path: Path | None = None
    if file_path is not None:
        resolved_path = Path(file_path)
        suffix = resolved_path.suffix.lower()
        if not suffix:
            derived_extension = determine_extension(filename=resolved_path.name)
            suffix = f".{derived_extension}" if derived_extension else ""
        upload_key = f"curve-input/{data_template_id}/{column_id}/{uuid.uuid4().hex[:10]}{suffix}"

    resolved_attachment_id = AttachmentId(
        resolve_attachment(
            attachment_collection=attachment_collection,
            task_id=data_template_id,
            file_path=resolved_path or file_path,
            attachment_id=str(attachment_id) if attachment_id else None,
            allowed_extensions=normalized_extensions,
            note_text=None,
            upload_key=upload_key,
        )
    )

    raw_attachment = attachment_collection.get_by_id(id=resolved_attachment_id)
    raw_key = raw_attachment.key
    if not raw_key:
        raise ValueError("Curve input attachment does not include an S3 key.")

    file_name = raw_attachment.name or ""
    attachment_extension = determine_extension(filename=file_name)
    normalized_extension = (attachment_extension or "").lower()
    if normalized_extensions and normalized_extension not in normalized_extensions:
        identifier = file_name or str(resolved_attachment_id)
        allowed_display = display_extensions or sorted(normalized_extensions)
        raise ValueError(
            f"Attachment '{identifier}' does not match required extensions {allowed_display}."
        )

    if require_signed_url and not raw_attachment.signed_url:
        raise ValueError("Attachment does not include a signed URL required for script execution.")

    return raw_attachment


def exec_curve_script(
    *,
    session: "AlbertSession",
    api_version: str,
    data_template_id: DataTemplateId,
    column_id: DataColumnId,
    raw_attachment: Attachment,
    file_collection: "FileCollection",
    script_attachment_signed_url: str,
) -> tuple[str, dict[str, str]]:
    """Execute the curve preprocessing script and return the processed key and column headers."""

    raw_signed_url = raw_attachment.signed_url
    if not raw_signed_url:
        raise ValueError("Curve input attachment does not include a signed URL.")

    processed_input_key = f"curve-input/{data_template_id}/{column_id}/{uuid.uuid4().hex}.csv"
    content_type = raw_attachment.mime_type or "text/csv"
    upload_url = file_collection.get_signed_upload_url(
        name=processed_input_key,
        namespace=FileNamespace.RESULT,
        content_type=content_type,
    )
    metadata_payload = TaskMetadata(filename=raw_attachment.name or "", task_id=data_template_id)
    csv_payload = CsvCurveInput(
        script_s3_url=script_attachment_signed_url,
        data_s3_url=raw_signed_url,
        result_s3_url=upload_url,
        task_metadata=metadata_payload,
    )
    response = session.post(
        f"/api/{api_version}/proxy/csvtable/curve",
        json=csv_payload.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    curve_response = CsvCurveResponse.model_validate(response.json())
    if curve_response.status.upper() != "OK":
        raise ValueError(
            f"Curve script execution failed: {curve_response.message or curve_response.status}."
        )
    column_headers = {
        key: value
        for key, value in curve_response.column_headers.items()
        if isinstance(key, str) and isinstance(value, str) and value
    }
    return processed_input_key, column_headers


def derive_curve_csv_mapping(
    *,
    target_column: DataColumnValue,
    column_headers: dict[str, str],
    field_mapping: dict[str, str] | None,
) -> dict[str, str]:
    """Derive the CSV-to-curve mapping for a target column."""

    header_sequence = list(column_headers.items())
    if not getattr(target_column, "curve_data", None):
        raise ValueError(
            f"Data column '{target_column.name}' does not define curve data entries to map."
        )

    column_to_csv_key = map_csv_headers_to_columns(
        header_sequence=header_sequence,
        data_columns=[target_column],
        field_mapping=field_mapping,
        use_curve_data_ids=True,
    )
    if not column_to_csv_key:
        raise ValueError(
            "Unable to map any data template columns to CSV headers. "
            "Ensure CSV headers match data template curve result column names."
        )

    header_lookup = dict(header_sequence)
    csv_mapping = {
        header_lookup[row_key]: data_col_id.lower()
        for data_col_id, row_key in column_to_csv_key.items()
        if row_key in header_lookup
    }
    if not csv_mapping:
        raise ValueError(
            "Column mapping could not be constructed from the CSV headers. "
            "Ensure the file contains data for the selected curve results."
        )

    return csv_mapping


def create_curve_import_job(
    *,
    session: "AlbertSession",
    data_template_id: DataTemplateId,
    column_id: DataColumnId,
    csv_mapping: dict[str, str],
    raw_attachment: Attachment,
    processed_input_key: str,
) -> tuple[str, str, str]:
    """Create the curve import job and wait for completion."""
    partition_uuid = str(uuid.uuid4())
    s3_output_key = (
        f"curve-output/{data_template_id}/{column_id}/"
        f"parentid=null/blockid=null/datatemplateid={data_template_id}/uuid={partition_uuid}"
    )
    namespace = raw_attachment.namespace or "result"
    worker_metadata = WorkerJobMetadata(
        parent_type="DAT",
        parent_id=data_template_id,
        table_name=f"{data_template_id.lower()}_{column_id.lower()}",
        mapping=csv_mapping,
        namespace=namespace,
        s3_input_key=processed_input_key,
        s3_output_key=s3_output_key,
    )
    worker_request = WorkerJobCreateRequest(
        job_type="importCurveData",
        metadata=worker_metadata,
    )
    job_response = session.post(
        "/api/v3/worker-jobs",
        json=worker_request.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    worker_job = WorkerJob.model_validate(job_response.json())
    job_id = worker_job.albert_id
    if not job_id:
        raise ValueError("Worker job creation did not return an identifier.")

    class _WorkerJobPending(Exception):
        """Internal sentinel exception indicating the worker job is still running."""

    @retry(
        stop=stop_after_attempt(_CURVE_JOB_MAX_ATTEMPTS),
        wait=wait_exponential(min=_CURVE_JOB_POLL_INTERVAL, max=_CURVE_JOB_MAX_WAIT),
        reraise=True,
    )
    def _poll_worker_job() -> WorkerJob:
        status_response = session.get(f"/api/v3/worker-jobs/{job_id}")
        current_job = WorkerJob.model_validate(status_response.json())
        state = current_job.state

        if state in WORKER_JOB_PENDING_STATES:
            logger.warning(
                "Curve data import in progress for template %s column %s",
                data_template_id,
                column_id,
            )
            raise _WorkerJobPending()
        return current_job

    try:
        worker_job = _poll_worker_job()
    except _WorkerJobPending as exc:
        raise TimeoutError(
            f"Worker job {job_id} did not complete within the retry window."
        ) from exc

    is_success = worker_job.state == WorkerJobState.SUCCESSFUL
    if not is_success:
        message = worker_job.state_message or "unknown failure"
        raise ValueError(f"Curve import worker job failed: {message}.")

    return job_id, partition_uuid, s3_output_key


def build_curve_import_patch_payload(
    *,
    target_column: DataColumnValue,
    job_id: str,
    csv_mapping: dict[str, str],
    raw_attachment: Attachment,
    partition_uuid: str,
    s3_output_key: str,
) -> GeneralPatchPayload:
    """Construct the patch payload applied after a successful curve import."""

    raw_key = raw_attachment.key
    if not raw_key:
        raise ValueError("Curve input attachment does not include an S3 key.")

    file_name = raw_attachment.name or ""
    value_payload = {
        "fileName": file_name,
        "s3Key": {
            "s3Input": raw_key,
            "rawfile": raw_key,
            "s3Output": s3_output_key,
        },
    }
    actions = [
        PGPatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="jobId",
            new_value=job_id,
        ),
        PGPatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="csvMapping",
            new_value=csv_mapping,
        ),
        PGPatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="value",
            new_value=value_payload,
        ),
        PGPatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="athenaPartitionKey",
            new_value=partition_uuid,
        ),
    ]
    return GeneralPatchPayload(
        data=[
            GeneralPatchDatum(
                attribute="datacolumn",
                colId=target_column.sequence,
                actions=actions,
            )
        ]
    )


def _validation_is_curve(validation: ValueValidation | dict | None) -> bool:
    if isinstance(validation, ValueValidation):
        return validation.datatype == DataType.CURVE
    if isinstance(validation, dict):
        datatype = validation.get("datatype")
        if isinstance(datatype, DataType):
            return datatype == DataType.CURVE
        if isinstance(datatype, str):
            return datatype.lower() == DataType.CURVE.value
    return False
