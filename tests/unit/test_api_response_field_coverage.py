"""Guard that models keep the API response fields their consumers depend on.

``BaseAlbertModel`` does not set an ``extra`` policy, so Pydantic defaults to
``extra="ignore"`` and any field a model fails to declare is dropped at validation
and is not recoverable from ``model_extra``. These tests pin the fields that were
silently lost, using payload fragments recorded from the live API.
"""

import pytest

from albert.resources.product_design import (
    CasLevelSubstance,
    UnpackedCasInfo,
    UnpackedProductDesign,
)
from albert.resources.projects import Project, ProjectClass, TaskConfig
from albert.resources.property_data import PropertyData, TaskDataColumn, TaskPropertyCreate
from albert.resources.substance import SubstanceInfo
from albert.resources.substance_v4 import SubstanceV4Info, SubstanceV4SearchItem

# Recorded from GET /api/v3/productdesign/DESIGN/unpack?formulaId=INVP603-004
CAS_LEVEL_SUBSTANCE_PAYLOAD = {
    "casPrimaryKeyId": "CAS39928",
    "casID": "68585-34-2",
    "amount": 0.24642857,
    "min": 0.19714286,
    "aggregatedFunc": [],
    "target": 0,
    "albertId": "INVA42942",
    "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b",
}


def test_cas_level_substance_keeps_substance_id():
    """The Regulatory DB key must survive validation, not be dropped as an extra."""
    substance = CasLevelSubstance.model_validate(CAS_LEVEL_SUBSTANCE_PAYLOAD)

    assert substance.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    assert substance.cas_id == "68585-34-2"
    assert substance.albert_id == "INVA42942"
    assert substance.min == pytest.approx(0.19714286)
    assert substance.target == pytest.approx(0)


def test_unpacked_product_design_exposes_substance_ids():
    """substance_id survives through the top-level unpack response model."""
    unpacked = UnpackedProductDesign.model_validate(
        {"casLevelSubstances": [CAS_LEVEL_SUBSTANCE_PAYLOAD]}
    )

    assert unpacked.cas_level_substances is not None
    assert unpacked.cas_level_substances[0].substance_id == (
        "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    )


def test_unpacked_cas_info_keeps_substance_id():
    cas_info = UnpackedCasInfo.model_validate(
        {"id": "CAS39928", "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"}
    )

    assert cas_info.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"


def test_substance_v4_info_declares_wgk():
    """``SubstanceV4Info`` must expose WGK as a typed field, matching its search sibling.

    Only ``region="DE"`` returns the field; the models must agree on the attribute
    name so callers do not need to know which endpoint produced the record.
    """
    info = SubstanceV4Info.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})
    search_item = SubstanceV4SearchItem.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})

    assert info.wgk == "WGK 1"
    assert search_item.wgk == "WGK 1"


def test_substance_v4_info_wgk_absent_outside_german_region():
    """Regions other than DE omit WGK; the model must not invent a value."""
    info = SubstanceV4Info.model_validate({"casID": "64-18-6"})

    assert info.wgk is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pdscl", {"maxValue": 1, "unit": "%"}),
        (
            "prtr",
            {
                "className": "Specified Class 1,Class 1",
                "unit": "%",
                "controlNumber": 411,
                "maxValue": 0.1,
            },
        ),
    ],
)
def test_substance_v4_info_accepts_japanese_object_fields(field, value):
    """``region="JP"`` returns objects for these; typing them as ``str`` raised."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0", field: value})

    assert getattr(info, field) == value


# Recorded from GET /api/v3/projects/{id}; TaskConfig entries arrive under the
# "TaskConfig" key with "dataTemplateId" and string "hidden" values.
PROJECT_TASK_CONFIG_PAYLOAD = {
    "dataTemplateId": "DAT123",
    "workflowId": "WFL123",
    "defaultTaskName": "Characterization",
    "target": "standard",
    "hidden": "true",
}


def test_project_task_config_deserializes_from_wire_names():
    """Test TaskConfig entries on a project survive validation, not dropped as extras."""
    project = Project.model_validate(
        {"description": "p", "TaskConfig": [PROJECT_TASK_CONFIG_PAYLOAD]}
    )

    assert len(project.task_config) == 1
    config = project.task_config[0]
    assert isinstance(config, TaskConfig)
    assert config.data_template_id == "DAT123"
    assert config.workflow_id == "WFL123"
    assert config.default_task_name == "Characterization"
    assert config.hidden == "true"


def test_project_task_config_serializes_to_wire_names():
    """Test TaskConfig dumps under "TaskConfig" with the API's inner field names."""
    project = Project(description="p", task_config=[TaskConfig(**PROJECT_TASK_CONFIG_PAYLOAD)])

    dumped = project.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["TaskConfig"] == [PROJECT_TASK_CONFIG_PAYLOAD]


def test_project_class_supports_restricted():
    """Test the restricted project class parses from API responses."""
    project = Project.model_validate({"description": "p", "class": "restricted"})

    assert project.project_class is ProjectClass.RESTRICTED


def test_project_old_api_params_uses_wire_name():
    """Test oldApiParams maps to old_api_params instead of being dropped."""
    project = Project.model_validate({"description": "p", "oldApiParams": {"moNumber": "42"}})

    assert project.old_api_params == {"moNumber": "42"}


# Recorded from GET /api/v3/propertydata?entity=task (DataColumns[].PropertyData)
TASK_PROPERTY_DATA_PAYLOAD = {
    "id": "PTD5495725",
    "value": "12",
    "valueNumeric": 12,
    "valueString": "Text value for cell",
    "valueType": "number",
}


def test_property_data_keeps_numeric_and_string_forms():
    """The typed value forms must survive validation, not be dropped as extras."""
    property_data = PropertyData.model_validate(TASK_PROPERTY_DATA_PAYLOAD)

    assert property_data.value == "12"
    assert property_data.value_numeric == 12
    assert property_data.value_string == "Text value for cell"


def test_task_property_create_sends_visible_trial_number_as_number():
    """``visibleTrialNo`` is a ``number`` in the API schema, not a string."""
    prop = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1", column_sequence="COL1"),
        value="1.2",
    )

    payload = prop.model_dump(by_alias=True, exclude_none=True, mode="json")

    assert isinstance(payload["visibleTrialNo"], int)
    assert payload["visibleTrialNo"] == 1


def test_substance_info_tolerates_wider_v3_field_types():
    """``SubstanceInfo`` fields whose v3 payloads are wider than first modeled.

    Per the api-substance-v3 spec, ``specificConcentrationLimit`` is an array of
    objects, ``mFactor``/``mFactorChronic`` may be strings, and the STOT fields
    may be objects; the narrow types raised ValidationError on real responses.
    """
    substance = SubstanceInfo.model_validate(
        {
            "casID": "50-00-0",
            "specificConcentrationLimit": [
                {"class": "Skin Corr.", "hCode": "H314", "category": "1"}
            ],
            "mFactor": "10",
            "mFactorChronic": "1",
            "stotAffectedOrgans": {"organ": "liver"},
            "stotRouteOfExposure": {"route": "oral"},
        }
    )

    assert isinstance(substance.specific_concentration_limit, list)
    assert substance.m_factor == "10"
    assert substance.m_factor_chronic == "1"
    assert substance.stot_affected_organs == {"organ": "liver"}
    assert substance.stot_route_of_exposure == {"route": "oral"}
