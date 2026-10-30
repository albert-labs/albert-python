"""Unit tests for the design-model-config resource models: wire round-trips and validators."""

import pytest
from pydantic import ValidationError

from albert.resources.design_model_configs import (
    CreateDesignModelConfigRequest,
    DesignModelConfig,
    DesignModelConfigApplyResponse,
    DesignModelConfigCreated,
    DesignModelConfigFeaturePreview,
    DesignModelConfigOperationsRequest,
    DesignModelConfigReferences,
    DesignModelConfigResolvedFeatures,
    DesignModelConfigValidationResponse,
    DesignModelConfigViolation,
    FamilySelector,
    FeatureMask,
    OutputEntry,
    SetOutputOperation,
)
from albert.resources.design_operands import (
    IngredientAmountOperand,
    LabelFractionOperand,
    ParameterOperand,
    PropertyAggregationOperand,
)
from albert.resources.design_spaces import RemoveComponentOperation, UpdateComponentOperation

_AUDIT = {"at": "2026-10-01T09:00:00Z", "by": "USR12", "byName": "Jane Doe"}


def test_design_model_config_round_trips_the_full_example():
    """Test that a fully populated config parses and re-serializes unchanged."""
    wire = {
        "id": "DMC123",
        "albertId": "DMC123",
        "schemaVersion": 1,
        "name": "Clearcoat surrogate",
        "description": "Feature and estimator choices for the 2027 EU clearcoat line.",
        "parentId": "PRO456",
        "state": "draft",
        "forkedFromId": None,
        "derivedFromId": "SDT789",
        "outputs": {
            "TAR045": {"dataType": "numeric", "outputTransform": "log"},
            "TAR046": {
                "dataType": "numeric",
                "features": {
                    "exclude": [
                        {"type": "allParameters"},
                        {"type": "ingredientAmount", "ingredient": "INV009"},
                    ]
                },
            },
            "TAR047": {"dataType": "categorical"},
        },
        "status": "active",
        "version": 2,
        "created": _AUDIT,
        "updated": {"at": "2026-10-02T11:30:00Z", "by": "USR12", "byName": "Jane Doe"},
    }

    config = DesignModelConfig.model_validate(wire)

    assert config.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        k: v for k, v in wire.items() if k not in {"albertId", "forkedFromId"}
    }


def test_create_request_example_uses_wire_field_names():
    """Test that the derived-create example serializes with the wire's camelCase names."""
    request = CreateDesignModelConfigRequest(
        name="Clearcoat surrogate",
        description="Feature and estimator choices for the 2027 EU clearcoat line.",
        parent_id="PRO456",
        smart_dataset_id="SDT789",
    )

    assert request.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        "name": "Clearcoat surrogate",
        "description": "Feature and estimator choices for the 2027 EU clearcoat line.",
        "parentId": "PRO456",
        "smartDatasetId": "SDT789",
    }


def test_operations_request_round_trips_the_wiring_example():
    """Test that the contract's operations example parses and re-serializes unchanged."""
    wire = {
        "operations": [
            {
                "op": "setOutput",
                "key": "TAR046",
                "value": {
                    "dataType": "numeric",
                    "features": {
                        "exclude": [
                            {"type": "allParameters"},
                            {"type": "ingredientAmount", "ingredient": "INV009"},
                        ]
                    },
                },
            },
            {
                "op": "updateComponent",
                "path": "outputs/TAR045",
                "field": "outputTransform",
                "value": "asinh",
            },
        ],
        "validate": True,
        "resolve": True,
        "dryRun": False,
    }

    request = DesignModelConfigOperationsRequest.model_validate(wire)

    assert request.model_dump(by_alias=True, mode="json", exclude_unset=True) == wire


def test_operation_union_discriminates_on_op_and_reuses_the_design_space_ops():
    """Test that each op parses to its class, and remove/update are the design-space ones."""
    request = DesignModelConfigOperationsRequest.model_validate(
        {
            "operations": [
                {"op": "setOutput", "key": "TAR1", "value": {"dataType": "numeric"}},
                {"op": "removeComponent", "path": "outputs/TAR2"},
                {
                    "op": "updateComponent",
                    "path": "outputs/TAR1",
                    "field": "dataType",
                    "value": "x",
                },
            ]
        }
    )

    kinds = [type(op) for op in request.operations]
    assert kinds == [SetOutputOperation, RemoveComponentOperation, UpdateComponentOperation]


def test_an_unknown_operation_is_rejected():
    """Test that an op outside the three supported kinds fails validation."""
    with pytest.raises(ValidationError):
        DesignModelConfigOperationsRequest.model_validate(
            {"operations": [{"op": "setIngredient", "key": "INV1", "value": {}}]}
        )


def test_set_output_keeps_the_op_and_mask_entry_types_when_left_to_default():
    """Test that defaulted discriminators survive the unset-field exclusion apply uses."""
    operation = SetOutputOperation(
        key="TAR1",
        value=OutputEntry(
            data_type="numeric",
            features=FeatureMask(include=[IngredientAmountOperand(ingredient="INV1")]),
        ),
    )

    sent = DesignModelConfigOperationsRequest(operations=[operation]).model_dump(
        by_alias=True, mode="json", exclude_unset=True
    )["operations"][0]

    assert sent == {
        "op": "setOutput",
        "key": "TAR1",
        "value": {
            "dataType": "numeric",
            "features": {"include": [{"type": "ingredientAmount", "ingredient": "INV1"}]},
        },
    }


@pytest.mark.parametrize(
    ("entry", "expected_type"),
    [
        ({"type": "allIngredientAmounts"}, FamilySelector),
        ({"type": "allLabelFractions"}, FamilySelector),
        ({"type": "allIngredientProperties"}, FamilySelector),
        ({"type": "allParameters"}, FamilySelector),
        ({"type": "ingredientAmount", "ingredient": "INV1"}, IngredientAmountOperand),
        ({"type": "labelFraction", "label": "TAG1"}, LabelFractionOperand),
        ({"type": "parameter", "parameter": "DAT1#PRM1#UNI1"}, ParameterOperand),
        (
            {
                "type": "propertyAggregation",
                "basis": "mean",
                "property": "density",
                "label": "TAG1",
                "impute": 0.5,
            },
            PropertyAggregationOperand,
        ),
    ],
)
def test_mask_entry_discriminates_on_type(entry, expected_type):
    """Test that a mask entry parses into the class named by its type and round-trips."""
    mask = FeatureMask.model_validate({"include": [entry]})

    assert isinstance(mask.include[0], expected_type)
    assert mask.model_dump(mode="json", by_alias=True, exclude_none=True) == {"include": [entry]}


def test_property_aggregation_impute_accepts_a_bool_or_a_number():
    """Test that impute is kept as a bool or a float, not coerced between them."""
    base = {"type": "propertyAggregation", "basis": "sum", "property": "density"}

    assert PropertyAggregationOperand.model_validate({**base, "impute": True}).impute is True
    assert PropertyAggregationOperand.model_validate({**base, "impute": 2.5}).impute == 2.5
    with pytest.raises(ValidationError):
        PropertyAggregationOperand.model_validate({**base, "basis": "median"})


def test_unknown_mask_entry_type_is_rejected():
    """Test that a mask entry kind the SDK does not model fails validation."""
    with pytest.raises(ValidationError):
        FeatureMask.model_validate({"exclude": [{"type": "extraFeature", "key": "MDF1"}]})


@pytest.mark.parametrize(
    "mask",
    [
        {},
        {"include": [{"type": "allParameters"}], "exclude": [{"type": "allParameters"}]},
        {"include": []},
        {"exclude": []},
    ],
    ids=["neither", "both", "empty include", "empty exclude"],
)
def test_feature_mask_needs_exactly_one_non_empty_list(mask):
    """Test that a mask with neither, both, or an empty list fails validation."""
    with pytest.raises(ValidationError):
        FeatureMask.model_validate(mask)


def test_output_entry_passes_beta_fields_through():
    """Test that fields the SDK does not model survive a parse and re-serialize."""
    wire = {"dataType": "numeric", "estimator": {"kind": "gp"}, "rationale": "because"}

    entry = OutputEntry.model_validate(wire)

    assert entry.model_dump(by_alias=True, mode="json", exclude_none=True) == wire


def test_output_entry_does_not_reject_a_transform_on_a_categorical_output():
    """Test that the transform rule is left to the service, as it is an apply-time check."""
    entry = OutputEntry(data_type="categorical", output_transform="log")

    assert entry.output_transform == "log"


def test_violation_accepts_the_contract_codes_and_rejects_others():
    """Test that every contract code parses and an unknown one fails validation."""
    for code in [
        "target_not_in_dataset",
        "transform_requires_positive_target",
        "inert_mask_entry",
        "feature_dropped_by_overlap",
        "estimator_downgraded",
        "unknown_reference",
        "dimension_not_modelled",
        "invalid_settings",
        "invalid_constraint",
    ]:
        assert (
            DesignModelConfigViolation.model_validate({"code": code, "message": "m"}).code == code
        )
    with pytest.raises(ValidationError):
        DesignModelConfigViolation.model_validate({"code": "surprise", "message": "m"})


def test_validation_response_with_violations_is_a_normal_result():
    """Test that valid=False with attributed violations parses."""
    result = DesignModelConfigValidationResponse.model_validate(
        {
            "valid": False,
            "violations": [
                {
                    "code": "target_not_in_dataset",
                    "message": "TAR9 is not in the dataset.",
                    "targetId": "TAR9",
                    "components": ["outputs/TAR9"],
                }
            ],
        }
    )

    assert result.valid is False
    assert result.violations[0].target_id == "TAR9"
    assert result.violations[0].components == ["outputs/TAR9"]


_RESOLVED = {
    "features": [
        {
            "key": "ingredient/INV001",
            "family": "ingredient_amount",
            "descriptor": {"type": "ingredientAmount", "ingredient": "INV001"},
            "origin": "default",
        },
        {
            "key": "parameter/DAT1#PRM1/high",
            "family": "parameter",
            "descriptor": {"type": "parameter", "parameter": "DAT1#PRM1"},
            "value": "high",
        },
        {
            "key": "property/mean/density/TAG1",
            "family": "ingredient_property",
            "descriptor": {
                "type": "propertyAggregation",
                "basis": "mean",
                "property": "density",
                "label": "TAG1",
            },
        },
        {
            "key": "label/TAG1",
            "family": "label_fraction",
            "descriptor": {"type": "labelFraction", "label": "TAG1"},
        },
    ],
    "outputs": {"TAR046": ["ingredient/INV001", "label/TAG1"]},
    "warnings": [
        {
            "code": "inert_mask_entry",
            "message": "Matches nothing.",
            "components": ["outputs/TAR046"],
        }
    ],
}


def test_resolved_features_parse_typed_descriptors_and_routing():
    """Test that a resolved-features payload parses into typed features and routing."""
    resolved = DesignModelConfigResolvedFeatures.model_validate(_RESOLVED)

    assert [type(f.descriptor) for f in resolved.features] == [
        IngredientAmountOperand,
        ParameterOperand,
        PropertyAggregationOperand,
        LabelFractionOperand,
    ]
    assert resolved.features[1].value == "high"
    assert resolved.features[2].origin == "default"
    assert resolved.outputs == {"TAR046": ["ingredient/INV001", "label/TAG1"]}
    assert resolved.warnings[0].code == "inert_mask_entry"


def test_resolved_features_keep_undeclared_keys():
    """Test that a field the SDK does not model survives on the resolved set."""
    resolved = DesignModelConfigResolvedFeatures.model_validate({**_RESOLVED, "extra": 1})

    assert resolved.model_dump()["extra"] == 1


_PREVIEW = {
    "numRows": 2,
    "rows": [
        {
            "experimentId": "INV001#LOT1#WFI1#TAS1#PRD1",
            "identifiers": {
                "type": "albert_measurement",
                "inventoryId": "INV001",
                "lotId": "LOT1",
                "workflowInterval": "WFI1",
                "taskId": "TAS1",
                "propertyDataId": "PRD1",
                "projectId": "PRO001",
            },
            "values": {"ingredient/INV001": 0.5, "label/TAG1": None},
        },
        {"experimentId": "EXP2", "values": {"ingredient/INV001": 0.4, "label/TAG1": 0.1}},
    ],
    "columnsTruncated": False,
    "summary": [
        {"key": "ingredient/INV001", "dtype": "float64", "nanCount": 0, "constant": False},
        {"key": "label/TAG1", "dtype": "float64", "nanCount": 1, "constant": True},
    ],
    "automaticFeatures": {"count": 2, "names": ["mol_wt", "logp"]},
    "warnings": [],
}


def test_feature_preview_parses_rows_summary_and_automatic_features():
    """Test that a feature-preview payload parses into typed rows and summaries."""
    preview = DesignModelConfigFeaturePreview.model_validate(_PREVIEW)

    assert preview.num_rows == 2
    assert preview.rows[0].experiment_id == "INV001#LOT1#WFI1#TAS1#PRD1"
    assert preview.rows[0].values["label/TAG1"] is None
    assert preview.summary[1].nan_count == 1
    assert preview.summary[1].constant is True
    assert preview.automatic_features.count == 2
    assert preview.automatic_features.names == ["mol_wt", "logp"]
    assert preview.columns_truncated is False


def test_feature_preview_row_parses_albert_identifiers():
    """Test that a preview row carries typed Albert identifiers, and None when absent."""
    preview = DesignModelConfigFeaturePreview.model_validate(_PREVIEW)

    identifiers = preview.rows[0].identifiers
    assert identifiers is not None
    assert identifiers.type == "albert_measurement"
    assert identifiers.inventory_id == "INV001"
    assert identifiers.lot_id == "LOT1"
    assert identifiers.property_data_id == "PRD1"
    assert preview.rows[1].identifiers is None


def test_apply_response_parses_every_folded_part():
    """Test that an apply result carries the config, validation, resolved set and preview."""
    result = DesignModelConfigApplyResponse.model_validate(
        {
            "modelConfig": {"id": "DMC123", "state": "draft", "outputs": {}},
            "validation": {"valid": True, "violations": []},
            "preview": _PREVIEW,
            "resolvedFeatures": _RESOLVED,
            "warnings": [{"code": "estimator_downgraded", "message": "m"}],
        }
    )

    assert result.design_model_config.id == "DMC123"
    assert result.validation.valid is True
    assert result.preview.num_rows == 2
    assert result.resolved_features.features[0].key == "ingredient/INV001"
    assert result.warnings[0].code == "estimator_downgraded"


def test_apply_response_without_the_optional_parts():
    """Test that an apply result with only the config parses, with empty warnings."""
    result = DesignModelConfigApplyResponse.model_validate({"modelConfig": {"id": "DMC123"}})

    assert result.validation is None
    assert result.preview is None
    assert result.resolved_features is None
    assert result.warnings == []


def test_references_preserve_undeclared_keys():
    """Test that the open-ended references document keeps unknown keys."""
    references = DesignModelConfigReferences.model_validate({"references": []})

    assert references.model_dump() == {"references": []}


def test_violation_carries_the_operation_it_came_from():
    """Test that a finding keeps the position of the operation behind it."""
    result = DesignModelConfigValidationResponse.model_validate(
        {
            "valid": False,
            "violations": [
                {"code": "invalid_settings", "message": "m", "opIndex": 1},
                {"code": "inert_mask_entry", "message": "m"},
            ],
        }
    )

    assert [v.op_index for v in result.violations] == [1, None]


def test_created_config_parses_a_variable_not_derived_warning():
    """Test that a derive warning for an unrepresentable target parses."""
    created = DesignModelConfigCreated.model_validate(
        {
            "id": "DMC123",
            "warnings": [
                {"code": "variable_not_derived", "message": "TAR9 has an unsupported type."}
            ],
        }
    )

    assert created.warnings[0].code == "variable_not_derived"
