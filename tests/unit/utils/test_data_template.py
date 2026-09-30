"""Unit tests for data-template curve/image helper functions."""

from __future__ import annotations

import pytest
import responses

from albert.collections.attachments import AttachmentCollection
from albert.core.shared.models.patch import GeneralPatchDatum, GeneralPatchPayload, PatchOperation
from albert.resources.attachments import Attachment
from albert.resources.data_templates import CurveDataEntityLink, DataColumnValue, DataTemplate
from albert.resources.parameter_groups import DataType, EnumValidationValue, ValueValidation
from albert.utils.data_template import (
    _validation_is_curve,
    _validation_is_image,
    build_curve_import_patch_payload,
    build_data_column_image_example_payload,
    derive_curve_csv_mapping,
    ensure_data_column_accepts_images,
    ensure_data_column_validation,
    get_script_attachment,
    get_target_data_column,
    prepare_curve_input_attachment,
    validate_data_column_type,
)
from tests.unit.conftest import UNIT_BASE_URL

# ---------------------------------------------------------------------------
# ensure_data_column_validation
# ---------------------------------------------------------------------------


def test_ensure_data_column_validation_skips_calculated_columns():
    """Test that a column with a calculation is left untouched."""
    column = DataColumnValue(data_column_id="DAC1", calculation="x + y")

    ensure_data_column_validation(column)

    assert column.validation == []


def test_ensure_data_column_validation_skips_when_already_typed():
    """Test that a column with an already-set validation datatype is left untouched."""
    column = DataColumnValue(
        data_column_id="DAC1", validation=[ValueValidation(datatype=DataType.STRING)]
    )

    ensure_data_column_validation(column)

    assert column.validation == [ValueValidation(datatype=DataType.STRING)]


def test_ensure_data_column_validation_curve_data_sets_curve_type():
    """Test that a column with curve_data defaults its validation to CURVE."""
    column = DataColumnValue(
        data_column_id="DAC1",
        curve_data=[CurveDataEntityLink(id="DAC2", name="X")],
    )

    ensure_data_column_validation(column)

    assert column.validation == [ValueValidation(datatype=DataType.CURVE)]


def test_ensure_data_column_validation_untyped_enum_list_value_sets_enum_type():
    """Test that an untyped validation entry with a list value defaults to ENUM."""
    options = [EnumValidationValue(text="Red"), EnumValidationValue(text="Blue")]
    column = DataColumnValue(
        data_column_id="DAC1",
        validation=[ValueValidation.model_construct(datatype=None, value=options)],
    )

    ensure_data_column_validation(column)

    assert column.validation == [ValueValidation(datatype=DataType.ENUM, value=options)]


def test_ensure_data_column_validation_defaults_to_number():
    """Test that a column with no calculation, curve data, or typed validation defaults to NUMBER."""
    column = DataColumnValue(data_column_id="DAC1")

    ensure_data_column_validation(column)

    assert column.validation == [ValueValidation(datatype=DataType.NUMBER)]


# ---------------------------------------------------------------------------
# get_target_data_column
# ---------------------------------------------------------------------------


def test_get_target_data_column_requires_exactly_one_identifier():
    """Test that providing both or neither of id/name raises ValueError."""
    template = DataTemplate(
        name="Tpl", data_column_values=[DataColumnValue(data_column_id="DAC1")]
    )

    with pytest.raises(ValueError, match="exactly one"):
        get_target_data_column(
            data_template=template,
            data_template_id="DAT1",
            data_column_id="DAC1",
            data_column_name="Viscosity",
        )

    with pytest.raises(ValueError, match="exactly one"):
        get_target_data_column(
            data_template=template,
            data_template_id="DAT1",
            data_column_id=None,
            data_column_name=None,
        )


def test_get_target_data_column_raises_when_template_has_no_columns():
    """Test that a template with no data columns raises ValueError."""
    template = DataTemplate(name="Tpl", data_column_values=None)

    with pytest.raises(ValueError, match="does not define any data columns"):
        get_target_data_column(
            data_template=template,
            data_template_id="DAT1",
            data_column_id="DAC1",
            data_column_name=None,
        )


def test_get_target_data_column_matches_by_id():
    """Test that a column is resolved by its exact id."""
    column = DataColumnValue(data_column_id="DAC1", name="Viscosity")
    template = DataTemplate(name="Tpl", data_column_values=[column])

    result = get_target_data_column(
        data_template=template,
        data_template_id="DAT1",
        data_column_id="DAC1",
        data_column_name=None,
    )

    assert result is column


def test_get_target_data_column_matches_by_name_case_insensitively():
    """Test that a column is resolved by name, ignoring case."""
    column = DataColumnValue(data_column_id="DAC1", name="Viscosity")
    template = DataTemplate(name="Tpl", data_column_values=[column])

    result = get_target_data_column(
        data_template=template,
        data_template_id="DAT1",
        data_column_id=None,
        data_column_name="viscosity",
    )

    assert result is column


def test_get_target_data_column_raises_when_no_match():
    """Test that an unmatched id or name raises ValueError naming the identifier."""
    template = DataTemplate(
        name="Tpl", data_column_values=[DataColumnValue(data_column_id="DAC1", name="Viscosity")]
    )

    with pytest.raises(ValueError, match="DAC-missing"):
        get_target_data_column(
            data_template=template,
            data_template_id="DAT1",
            data_column_id="DAC-missing",
            data_column_name=None,
        )


# ---------------------------------------------------------------------------
# validate_data_column_type / ensure_data_column_accepts_images
# ---------------------------------------------------------------------------


def test_validate_data_column_type_accepts_curve_column():
    """Test that a column with a CURVE validation entry passes validation."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Curve Col",
        validation=[ValueValidation(datatype=DataType.CURVE)],
    )

    validate_data_column_type(target_column=column)


@pytest.mark.parametrize(
    "validation",
    [
        pytest.param(None, id="unset"),
        pytest.param([], id="empty"),
        pytest.param([ValueValidation(datatype=DataType.NUMBER)], id="wrong-type"),
    ],
)
def test_validate_data_column_type_rejects_non_curve_column(validation):
    """Test that a non-curve column raises ValueError naming the column."""
    column = DataColumnValue(data_column_id="DAC1", name="Not Curve", validation=validation)

    with pytest.raises(ValueError, match="Not Curve"):
        validate_data_column_type(target_column=column)


def test_ensure_data_column_accepts_images_accepts_image_column():
    """Test that a column with an IMAGE validation entry passes validation."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Image Col",
        validation=[ValueValidation(datatype=DataType.IMAGE)],
    )

    ensure_data_column_accepts_images(target_column=column)


def test_ensure_data_column_accepts_images_rejects_non_image_column():
    """Test that a non-image column raises ValueError naming the column."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Not Image",
        validation=[ValueValidation(datatype=DataType.CURVE)],
    )

    with pytest.raises(ValueError, match="Not Image"):
        ensure_data_column_accepts_images(target_column=column)


# ---------------------------------------------------------------------------
# _validation_is_curve / _validation_is_image
# ---------------------------------------------------------------------------


def test_validation_is_curve_true_only_for_curve_datatype():
    """Test that _validation_is_curve only accepts a ValueValidation with datatype CURVE."""
    assert _validation_is_curve(ValueValidation(datatype=DataType.CURVE)) is True
    assert _validation_is_curve(ValueValidation(datatype=DataType.NUMBER)) is False
    assert _validation_is_curve(None) is False


def test_validation_is_image_true_only_for_image_datatype():
    """Test that _validation_is_image only accepts a ValueValidation with datatype IMAGE."""
    assert _validation_is_image(ValueValidation(datatype=DataType.IMAGE)) is True
    assert _validation_is_image(ValueValidation(datatype=DataType.CURVE)) is False
    assert _validation_is_image(None) is False


# ---------------------------------------------------------------------------
# derive_curve_csv_mapping
# ---------------------------------------------------------------------------


def test_derive_curve_csv_mapping_requires_curve_data():
    """Test that a column without curve_data raises ValueError."""
    column = DataColumnValue(data_column_id="DAC1", name="Curve Col")

    with pytest.raises(ValueError, match="does not define curve data entries"):
        derive_curve_csv_mapping(
            target_column=column, column_headers={"col0": "X"}, field_mapping=None
        )


def test_derive_curve_csv_mapping_builds_header_to_lowercased_id_mapping():
    """Test that a matched curve entry maps its CSV header to the lowercased column id."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Curve Col",
        curve_data=[CurveDataEntityLink(id="DAC2", name="X Values")],
    )

    result = derive_curve_csv_mapping(
        target_column=column, column_headers={"col0": "X Values"}, field_mapping=None
    )

    assert result == {"X Values": "dac2"}


def test_derive_curve_csv_mapping_raises_when_no_headers_match():
    """Test that no matching CSV header raises ValueError."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Curve Col",
        curve_data=[CurveDataEntityLink(id="DAC2", name="X Values")],
    )

    with pytest.raises(ValueError, match="Unable to map"):
        derive_curve_csv_mapping(
            target_column=column, column_headers={"col0": "Unrelated"}, field_mapping=None
        )


# ---------------------------------------------------------------------------
# build_curve_import_patch_payload
# ---------------------------------------------------------------------------


def test_build_curve_import_patch_payload_requires_s3_key():
    """Test that a raw attachment without a key raises ValueError."""
    column = DataColumnValue(data_column_id="DAC1", sequence="1")
    raw_attachment = Attachment(parent_id="DAT1", name="raw.csv", key="")

    with pytest.raises(ValueError, match="S3 key"):
        build_curve_import_patch_payload(
            target_column=column,
            job_id="JOB1",
            csv_mapping={"X Values": "dac2"},
            raw_attachment=raw_attachment,
            partition_uuid="uuid-1",
            s3_output_key="curve-output/key",
        )


def test_build_curve_import_patch_payload_builds_expected_actions():
    """Test that the curve import patch payload carries job id, mapping, and S3 keys."""
    column = DataColumnValue(data_column_id="DAC1", sequence="1")
    raw_attachment = Attachment(parent_id="DAT1", name="raw.csv", key="DAT1/raw.csv")

    payload = build_curve_import_patch_payload(
        target_column=column,
        job_id="JOB1",
        csv_mapping={"X Values": "dac2"},
        raw_attachment=raw_attachment,
        partition_uuid="uuid-1",
        s3_output_key="curve-output/key",
    )

    assert isinstance(payload, GeneralPatchPayload)
    assert len(payload.data) == 1
    datum = payload.data[0]
    assert isinstance(datum, GeneralPatchDatum)
    assert datum.attribute == "datacolumn"
    assert datum.colId == "1"
    assert [action.attribute for action in datum.actions] == [
        "jobId",
        "csvMapping",
        "value",
        "athenaPartitionKey",
    ]
    assert datum.actions[0].new_value == "JOB1"
    assert datum.actions[1].new_value == {"X Values": "dac2"}
    assert datum.actions[2].new_value == {
        "fileName": "raw.csv",
        "s3Key": {
            "s3Input": "DAT1/raw.csv",
            "rawfile": "DAT1/raw.csv",
            "s3Output": "curve-output/key",
        },
    }
    assert datum.actions[3].new_value == "uuid-1"
    assert all(action.operation == PatchOperation.ADD.value for action in datum.actions)


# ---------------------------------------------------------------------------
# build_data_column_image_example_payload
# ---------------------------------------------------------------------------


def test_build_data_column_image_example_payload_requires_s3_key():
    """Test that an image attachment without a key raises ValueError."""
    column = DataColumnValue(data_column_id="DAC1", sequence="1")
    attachment = Attachment(parent_id="DAT1", name="pic.png", key="")

    with pytest.raises(ValueError, match="S3 key"):
        build_data_column_image_example_payload(target_column=column, attachment=attachment)


def test_build_data_column_image_example_payload_requires_column_sequence():
    """Test that a column with no sequence raises ValueError."""
    column = DataColumnValue.model_construct(data_column_id="DAC1", sequence=None)
    attachment = Attachment(parent_id="DAT1", name="pic.png", key="DAT1/pic.png")

    with pytest.raises(ValueError, match="sequence is required"):
        build_data_column_image_example_payload(target_column=column, attachment=attachment)


def test_build_data_column_image_example_payload_builds_expected_action():
    """Test that the image example payload sets original/thumb/preview to the same S3 key."""
    column = DataColumnValue(data_column_id="DAC1", sequence="2")
    attachment = Attachment(parent_id="DAT1", name="pic.png", key="DAT1/pic.png")

    payload = build_data_column_image_example_payload(target_column=column, attachment=attachment)

    datum = payload.data[0]
    assert datum.colId == "2"
    action = datum.actions[0]
    assert action.attribute == "value"
    assert action.operation == PatchOperation.ADD.value
    assert action.new_value == {
        "fileName": "pic.png",
        "s3Key": {
            "original": "DAT1/pic.png",
            "thumb": "DAT1/pic.png",
            "preview": "DAT1/pic.png",
        },
    }


# ---------------------------------------------------------------------------
# get_script_attachment (I/O via responses)
# ---------------------------------------------------------------------------


@responses.activate
def test_get_script_attachment_returns_attachment_and_extensions(offline_session):
    """Test that the script attachment and its allowed extensions are returned."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/parents",
        json=[
            {
                "parentId": "DAT1",
                "Items": [
                    {
                        "albertId": "ATT1",
                        "name": "script.py",
                        "key": "DAT1/script.py",
                        "category": "Script",
                        "signedURL": "https://signed.example/script.py",
                        "Metadata": {"extensions": [{"id": "X", "name": "csv"}]},
                    }
                ],
            }
        ],
    )
    collection = AttachmentCollection(session=offline_session)

    attachment, extensions = get_script_attachment(
        attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
    )

    assert attachment.id == "ATT1"
    assert extensions == {"csv"}


@responses.activate
def test_get_script_attachment_raises_when_no_candidates_found(offline_session):
    """Test that an empty parent-map response raises ValueError."""
    responses.get(f"{UNIT_BASE_URL}/api/v3/attachments/parents", json=[])
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="no active script attachment"):
        get_script_attachment(
            attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
        )


@responses.activate
def test_get_script_attachment_raises_when_category_is_not_script(offline_session):
    """Test that a non-script attachment category raises ValueError."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/parents",
        json=[
            {
                "parentId": "DAT1",
                "Items": [
                    {"albertId": "ATT1", "name": "doc.pdf", "key": "k", "category": "Other"}
                ],
            }
        ],
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="is not a script"):
        get_script_attachment(
            attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
        )


@responses.activate
def test_get_script_attachment_raises_when_missing_signed_url(offline_session):
    """Test that a script attachment without a signed URL raises ValueError."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/parents",
        json=[
            {
                "parentId": "DAT1",
                "Items": [
                    {"albertId": "ATT1", "name": "script.py", "key": "k", "category": "Script"}
                ],
            }
        ],
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="signed URL"):
        get_script_attachment(
            attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
        )


@responses.activate
def test_get_script_attachment_raises_value_error_on_404(offline_session):
    """Test that a 404 from the API is surfaced as a ValueError, not an HTTP error."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/parents", status=404, json={"message": "not found"}
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="no script attached"):
        get_script_attachment(
            attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
        )


@responses.activate
def test_get_script_attachment_reraises_non_404_http_errors(offline_session):
    """Test that a non-404 HTTP error from the API is not swallowed into a ValueError."""
    from albert.exceptions import AlbertHTTPError

    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/parents",
        status=500,
        json={"message": "server error"},
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(AlbertHTTPError):
        get_script_attachment(
            attachment_collection=collection, data_template_id="DAT1", column_id="DAC1"
        )


# ---------------------------------------------------------------------------
# prepare_curve_input_attachment (I/O via responses, attachment_id path only)
# ---------------------------------------------------------------------------


def test_prepare_curve_input_attachment_requires_exactly_one_source(offline_session):
    """Test that providing both or neither of attachment_id/file_path raises ValueError."""
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="exactly one"):
        prepare_curve_input_attachment(
            attachment_collection=collection,
            data_template_id="DAT1",
            column_id="DAC1",
            allowed_extensions={"csv"},
            file_path="foo.csv",
            attachment_id="ATT1",
            require_signed_url=False,
        )

    with pytest.raises(ValueError, match="exactly one"):
        prepare_curve_input_attachment(
            attachment_collection=collection,
            data_template_id="DAT1",
            column_id="DAC1",
            allowed_extensions={"csv"},
            file_path=None,
            attachment_id=None,
            require_signed_url=False,
        )


@responses.activate
def test_prepare_curve_input_attachment_requires_s3_key(offline_session):
    """Test that a resolved attachment without a key raises ValueError."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/ATT1",
        json={"albertId": "ATT1", "parentId": "DAT1", "name": "raw.csv", "key": ""},
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="S3 key"):
        prepare_curve_input_attachment(
            attachment_collection=collection,
            data_template_id="DAT1",
            column_id="DAC1",
            allowed_extensions={"csv"},
            file_path=None,
            attachment_id="ATT1",
            require_signed_url=False,
        )


@responses.activate
def test_prepare_curve_input_attachment_rejects_mismatched_extension(offline_session):
    """Test that an attachment whose extension isn't allowed raises ValueError."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/ATT1",
        json={"albertId": "ATT1", "parentId": "DAT1", "name": "raw.txt", "key": "DAT1/raw.txt"},
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="does not match required extensions"):
        prepare_curve_input_attachment(
            attachment_collection=collection,
            data_template_id="DAT1",
            column_id="DAC1",
            allowed_extensions={"csv"},
            file_path=None,
            attachment_id="ATT1",
            require_signed_url=False,
        )


@responses.activate
def test_prepare_curve_input_attachment_requires_signed_url_when_needed(offline_session):
    """Test that require_signed_url=True raises ValueError when the attachment lacks one."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/ATT1",
        json={"albertId": "ATT1", "parentId": "DAT1", "name": "raw.csv", "key": "DAT1/raw.csv"},
    )
    collection = AttachmentCollection(session=offline_session)

    with pytest.raises(ValueError, match="signed URL"):
        prepare_curve_input_attachment(
            attachment_collection=collection,
            data_template_id="DAT1",
            column_id="DAC1",
            allowed_extensions={"csv"},
            file_path=None,
            attachment_id="ATT1",
            require_signed_url=True,
        )


@responses.activate
def test_prepare_curve_input_attachment_returns_attachment_when_valid(offline_session):
    """Test that a valid, matching, signed attachment is returned as-is."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/attachments/ATT1",
        json={
            "albertId": "ATT1",
            "parentId": "DAT1",
            "name": "raw.csv",
            "key": "DAT1/raw.csv",
            "signedURL": "https://signed.example/raw.csv",
        },
    )
    collection = AttachmentCollection(session=offline_session)

    attachment = prepare_curve_input_attachment(
        attachment_collection=collection,
        data_template_id="DAT1",
        column_id="DAC1",
        allowed_extensions={"csv"},
        file_path=None,
        attachment_id="ATT1",
        require_signed_url=True,
    )

    assert attachment.id == "ATT1"
    assert attachment.key == "DAT1/raw.csv"
