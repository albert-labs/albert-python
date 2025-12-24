"""Utilities for working with data templates."""

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from tenacity import retry, stop_after_attempt, wait_exponential

from albert.collections.attachments import AttachmentCollection
from albert.collections.files import FileCollection
from albert.core.logging import logger
from albert.core.shared.identifiers import AttachmentId, DataColumnId, DataTemplateId
from albert.core.shared.models.patch import (
    GeneralPatchDatum,
    GeneralPatchPayload,
    PatchDatum,
    PatchOperation,
)
from albert.exceptions import AlbertHTTPError
from albert.resources.attachments import Attachment, AttachmentCategory
from albert.resources.data_templates import DataColumnValue, DataTemplate, ImportMode
from albert.resources.files import FileNamespace
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    ParameterValue,
    ValueValidation,
)
from albert.resources.tasks import CsvCurveInput, CsvCurveResponse, TaskMetadata
from albert.resources.worker_jobs import (
    WORKER_JOB_PENDING_STATES,
    WorkerJob,
    WorkerJobCreateRequest,
    WorkerJobMetadata,
    WorkerJobState,
)
from albert.utils.tasks import (
    CSV_EXTENSIONS,
    determine_extension,
    extract_extensions_from_attachment,
    fetch_csv_table_rows,
    map_csv_headers_to_columns,
    resolve_attachment,
)

if TYPE_CHECKING:
    from albert.core.session import AlbertSession
    from albert.resources.data_templates import CurveExample, ImageExample


_CURVE_JOB_POLL_INTERVAL = 2.0
_CURVE_JOB_MAX_ATTEMPTS = 20
_CURVE_JOB_MAX_WAIT = 10.0
SUPPORTED_IMAGE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".jfif",
    ".pjpeg",
    ".pjp",
    ".svg",
    ".gif",
    ".apng",
    ".avif",
    ".webp",
    ".bmp",
    ".ico",
    ".cur",
    ".tif",
    ".tiff",
    ".heic",
]


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
        "/api/v3/proxy/csvtable/curve",
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
            logger.info(
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
        PatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="jobId",
            new_value=job_id,
        ),
        PatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="csvMapping",
            new_value=csv_mapping,
        ),
        PatchDatum(
            operation=PatchOperation.ADD.value,
            attribute="value",
            new_value=value_payload,
        ),
        PatchDatum(
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


def add_parameter_enums(
    *,
    session: "AlbertSession",
    base_path: str,
    data_template_id: DataTemplateId,
    new_parameters: list[ParameterValue],
) -> dict[str, list[EnumValidationValue]]:
    """Add enum values to newly created parameters and return updated enum sequences."""

    data_template = DataTemplate(**session.get(f"{base_path}/{data_template_id}").json())
    existing_parameters = data_template.parameter_values or []
    enums_by_sequence: dict[str, list[EnumValidationValue]] = {}
    for parameter in new_parameters:
        this_sequence = next(
            (
                p.sequence
                for p in existing_parameters
                if p.id == parameter.id and p.short_name == parameter.short_name
            ),
            None,
        )
        enum_patches: list[dict[str, str]] = []
        if (
            parameter.validation
            and len(parameter.validation) > 0
            and isinstance(parameter.validation[0].value, list)
        ):
            existing_validation = (
                [x for x in existing_parameters if x.sequence == parameter.sequence]
                if existing_parameters
                else []
            )
            existing_enums = (
                [
                    x
                    for x in existing_validation[0].validation[0].value
                    if isinstance(x, EnumValidationValue) and x.id is not None
                ]
                if (
                    existing_validation
                    and len(existing_validation) > 0
                    and existing_validation[0].validation
                    and len(existing_validation[0].validation) > 0
                    and existing_validation[0].validation[0].value
                    and isinstance(existing_validation[0].validation[0].value, list)
                )
                else []
            )
            updated_enums = (
                [x for x in parameter.validation[0].value if isinstance(x, EnumValidationValue)]
                if parameter.validation[0].value
                else []
            )

            deleted_enums = [
                x for x in existing_enums if x.id not in [y.id for y in updated_enums]
            ]

            new_enums = [x for x in updated_enums if x.id not in [y.id for y in existing_enums]]

            matching_enums = [x for x in updated_enums if x.id in [y.id for y in existing_enums]]

            for new_enum in new_enums:
                enum_patches.append({"operation": "add", "text": new_enum.text})
            for deleted_enum in deleted_enums:
                enum_patches.append({"operation": "delete", "id": deleted_enum.id})
            for matching_enum in matching_enums:
                if (
                    matching_enum.text
                    != [x for x in existing_enums if x.id == matching_enum.id][0].text
                ):
                    enum_patches.append(
                        {
                            "operation": "update",
                            "id": matching_enum.id,
                            "text": matching_enum.text,
                        }
                    )

            if enum_patches and this_sequence:
                enum_response = session.put(
                    f"{base_path}/{data_template_id}/parameters/{this_sequence}/enums",
                    json=enum_patches,
                )
                enums_by_sequence[this_sequence] = [
                    EnumValidationValue(**x) for x in enum_response.json()
                ]

    return enums_by_sequence


def upload_image_example_attachment(
    *,
    attachment_collection: "AttachmentCollection",
    data_template_id: DataTemplateId,
    file_path: str | Path | None,
    attachment_id: AttachmentId | None,
    upload_key: str | None = None,
) -> Attachment:
    """Upload or resolve an image attachment for a data template example."""

    supported_extensions = {ext.lstrip(".").lower() for ext in SUPPORTED_IMAGE_EXTENSIONS}
    resolved_attachment_id = AttachmentId(
        resolve_attachment(
            attachment_collection=attachment_collection,
            task_id=data_template_id,
            file_path=file_path,
            attachment_id=str(attachment_id) if attachment_id else None,
            allowed_extensions=supported_extensions,
            note_text=None,
            upload_key=upload_key,
        )
    )
    attachment = attachment_collection.get_by_id(id=resolved_attachment_id)
    if supported_extensions:
        attachment_ext = determine_extension(filename=attachment.name)
        if attachment_ext and attachment_ext not in supported_extensions:
            raise ValueError(
                f"Attachment '{attachment.name}' is not a supported image type "
                f"({sorted(supported_extensions)})."
            )
    return attachment


def build_data_column_image_example_payload(
    *,
    target_column: DataColumnValue,
    attachment: Attachment,
) -> GeneralPatchPayload:
    """Construct the patch payload to set an image example on a data column."""

    key = attachment.key
    file_name = attachment.name
    if not key:
        raise ValueError("Image attachment is missing an S3 key.")
    if target_column.sequence is None:
        raise ValueError("Data column sequence is required to patch image examples.")

    value_payload = {
        "fileName": file_name,
        "s3Key": {
            "original": key,
            "thumb": key,
            "preview": key,
        },
    }
    action = PatchDatum(
        operation=PatchOperation.ADD.value,
        attribute="value",
        new_value=value_payload,
    )
    return GeneralPatchPayload(
        data=[
            GeneralPatchDatum(
                attribute="datacolumn",
                colId=target_column.sequence,
                actions=[action],
            )
        ]
    )


def ensure_data_column_accepts_images(*, target_column: DataColumnValue) -> None:
    """Ensure the resolved data column is configured for image data."""

    validations = target_column.validation or []
    if not any(_validation_is_image(validation) for validation in validations):
        raise ValueError(
            f"Data column '{target_column.name}' must be an image-type column to add image examples."
        )


def _validation_is_curve(validation: ValueValidation | None) -> bool:
    return isinstance(validation, ValueValidation) and validation.datatype == DataType.CURVE


def _validation_is_image(validation: ValueValidation | None) -> bool:
    return isinstance(validation, ValueValidation) and validation.datatype == DataType.IMAGE


def build_curve_example(
    *,
    session: "AlbertSession",
    data_template_id: DataTemplateId,
    example: "CurveExample",
    target_column: DataColumnValue,
) -> GeneralPatchPayload:
    """Construct the patch payload for a curve example on a data template."""

    validate_data_column_type(target_column=target_column)
    column_id = target_column.data_column_id
    if column_id is None:
        raise ValueError("Target data column is missing an identifier.")
    attachment_collection = AttachmentCollection(session=session)
    file_collection = FileCollection(session=session)

    script_attachment_signed_url: str | None = None

    if example.mode is ImportMode.SCRIPT:
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
    raw_attachment = prepare_curve_input_attachment(
        attachment_collection=attachment_collection,
        data_template_id=data_template_id,
        column_id=column_id,
        allowed_extensions=allowed_extensions,
        file_path=example.file_path,
        attachment_id=example.attachment_id,
        require_signed_url=example.mode is ImportMode.SCRIPT,
    )
    raw_key = raw_attachment.key
    if raw_attachment.id is None:
        raise ValueError("Curve input attachment did not return an identifier.")
    resolved_attachment_id = AttachmentId(raw_attachment.id)

    processed_input_key: str = raw_key
    column_headers: dict[str, str] = {}

    if example.mode is ImportMode.SCRIPT:
        processed_input_key, column_headers = exec_curve_script(
            session=session,
            data_template_id=data_template_id,
            column_id=column_id,
            raw_attachment=raw_attachment,
            file_collection=file_collection,
            script_attachment_signed_url=script_attachment_signed_url,
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
        field_mapping=example.field_mapping,
    )

    job_id, partition_uuid, s3_output_key = create_curve_import_job(
        session=session,
        data_template_id=data_template_id,
        column_id=column_id,
        csv_mapping=csv_mapping,
        raw_attachment=raw_attachment,
        processed_input_key=processed_input_key,
    )

    return build_curve_import_patch_payload(
        target_column=target_column,
        job_id=job_id,
        csv_mapping=csv_mapping,
        raw_attachment=raw_attachment,
        partition_uuid=partition_uuid,
        s3_output_key=s3_output_key,
    )


def build_image_example(
    *,
    session: "AlbertSession",
    data_template_id: DataTemplateId,
    example: "ImageExample",
    target_column: DataColumnValue,
) -> GeneralPatchPayload:
    """Construct the patch payload for an image example on a data template."""

    ensure_data_column_accepts_images(target_column=target_column)
    resolved_path = Path(example.file_path)
    upload_ext = resolved_path.suffix.lower()
    if not upload_ext:
        raise ValueError("File extension is required for image examples.")
    upload_key = f"imagedata/original/{data_template_id}/{uuid.uuid4().hex[:10]}{upload_ext}"
    attachment_collection = AttachmentCollection(session=session)
    attachment = upload_image_example_attachment(
        attachment_collection=attachment_collection,
        data_template_id=data_template_id,
        file_path=example.file_path,
        attachment_id=None,
        upload_key=upload_key,
    )
    return build_data_column_image_example_payload(
        target_column=target_column, attachment=attachment
    )
