"""Unit tests for the design-space resource models: wire round-trips and validators."""

import pytest
from pydantic import ValidationError

from albert.resources.design_spaces import (
    CategoricalConstraint,
    ContinuousConstraint,
    CreateDesignSpaceRequest,
    DesignSpace,
    DesignSpaceOperationsRequest,
    DesignSpaceReferences,
    DesignSpaceSample,
    DesignSpaceViolation,
    DiscreteConstraint,
    ParameterEntry,
    SetCountBoundsOperation,
)


def test_design_space_round_trips_a_full_document():
    """Test that a fully populated design space parses and re-serializes unchanged."""
    wire = {
        "id": "DSP123",
        "albertId": "DSP123",
        "schemaVersion": 1,
        "name": "Low-VOC clearcoat envelope",
        "description": "Regulatory envelope for the 2027 EU clearcoat line.",
        "parentId": "PRO456",
        "state": "draft",
        "forkedFromId": None,
        "derivedFromId": "SDT789",
        "maxCount": 4,
        "parameters": {
            "DAT01#PRM07#UNI12": {
                "ref": {
                    "parameterId": "PRM07",
                    "dataTemplateId": "DAT01",
                    "parameterGroupId": None,
                    "unitId": "UNI12",
                },
                "dataType": "numeric",
                "constraint": {"type": "continuous", "min": 60, "max": 120},
            }
        },
        "ingredients": {
            "INV001": {"action": "mustInclude", "min": 0.40, "max": 0.65},
            "INV002": {"action": "mustInclude", "min": 0.15, "max": 0.30},
            "INV004": {"action": "mayInclude", "min": 0.0, "max": 0.03},
            "INV009": {"action": "exclude"},
        },
        "status": "active",
        "version": 3,
        "created": {"at": "2026-10-01T09:00:00Z", "by": "USR12", "byName": "Jane Doe"},
        "updated": {"at": "2026-10-02T11:30:00Z", "by": "USR12", "byName": "Jane Doe"},
    }

    space = DesignSpace.model_validate(wire)

    # The wire carries both `id` and `albertId` with the same value; the model exposes
    # the ID once, as `id`. Explicit nulls on the wire (`forkedFromId`) are not
    # re-serialized.
    assert space.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        "id": "DSP123",
        "schemaVersion": 1,
        "name": "Low-VOC clearcoat envelope",
        "description": "Regulatory envelope for the 2027 EU clearcoat line.",
        "parentId": "PRO456",
        "state": "draft",
        "derivedFromId": "SDT789",
        "maxCount": 4,
        "parameters": {
            "DAT01#PRM07#UNI12": {
                "ref": {
                    "parameterId": "PRM07",
                    "dataTemplateId": "DAT01",
                    "unitId": "UNI12",
                },
                "dataType": "numeric",
                "constraint": {"type": "continuous", "min": 60.0, "max": 120.0},
            }
        },
        "ingredients": {
            "INV001": {"action": "mustInclude", "min": 0.4, "max": 0.65},
            "INV002": {"action": "mustInclude", "min": 0.15, "max": 0.3},
            "INV004": {"action": "mayInclude", "min": 0.0, "max": 0.03},
            "INV009": {"action": "exclude"},
        },
        "status": "active",
        "version": 3,
        "created": {"at": "2026-10-01T09:00:00Z", "by": "USR12", "byName": "Jane Doe"},
        "updated": {"at": "2026-10-02T11:30:00Z", "by": "USR12", "byName": "Jane Doe"},
    }


def test_operations_request_round_trips_a_mixed_operation_list():
    """Test that a mixed builder-operation list parses and re-serializes unchanged."""
    wire = {
        "operations": [
            {
                "op": "setParameter",
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": "UNI12",
                "value": {
                    "dataType": "numeric",
                    "constraint": {"type": "continuous", "min": 60, "max": 120},
                },
            },
            {"op": "updateComponent", "path": "ingredients/INV004", "field": "max", "value": 0.03},
            {"op": "removeComponent", "path": "ingredients/INV099"},
        ],
        "validate": True,
        "preview": {"numSamples": 5},
        "dryRun": False,
    }

    request = DesignSpaceOperationsRequest.model_validate(wire)

    assert request.model_dump(by_alias=True, mode="json", exclude_unset=True) == {
        "operations": [
            {
                "op": "setParameter",
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": "UNI12",
                "value": {
                    "dataType": "numeric",
                    "constraint": {"type": "continuous", "min": 60.0, "max": 120.0},
                },
            },
            {
                "op": "updateComponent",
                "path": "ingredients/INV004",
                "field": "max",
                "value": 0.03,
            },
            {"op": "removeComponent", "path": "ingredients/INV099"},
        ],
        "validate": True,
        "preview": {"numSamples": 5},
        "dryRun": False,
    }


def test_create_request_uses_wire_field_names():
    """Test that the create body serializes with the wire's camelCase names."""
    request = CreateDesignSpaceRequest(
        name="Derived envelope",
        parent_id="PRO456",
        description="From history.",
        smart_dataset_id="SDT789",
    )

    assert request.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        "name": "Derived envelope",
        "parentId": "PRO456",
        "description": "From history.",
        "smartDatasetId": "SDT789",
    }


@pytest.mark.parametrize(
    "constraint,expected_type",
    [
        ({"type": "continuous", "min": 60, "max": 120}, ContinuousConstraint),
        ({"type": "discrete", "values": [1.0, 2.5]}, DiscreteConstraint),
        ({"type": "categorical", "values": ["low", "high"]}, CategoricalConstraint),
    ],
    ids=["continuous", "discrete", "categorical"],
)
def test_parameter_entry_constraint_discriminates_on_type(constraint, expected_type):
    """Test that a parameter constraint parses into the subtype named by its type."""
    entry = ParameterEntry.model_validate(
        {
            "ref": {
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": None,
            },
            "dataType": "numeric",
            "constraint": constraint,
        }
    )

    assert isinstance(entry.constraint, expected_type)


@pytest.mark.parametrize(
    "ref",
    [
        {"parameterId": "PRM1", "dataTemplateId": "DAT1"},
        {"parameterId": "PRM1", "parameterGroupId": "PRG1", "unitId": "UNI1"},
    ],
)
def test_parameter_ref_parses_without_the_absent_nullable_ids(ref):
    """Test that a parameter ref with its unused container and unit keys left out parses."""
    entry = ParameterEntry.model_validate(
        {
            "ref": ref,
            "dataType": "numeric",
            "constraint": {"type": "continuous", "min": 1.0, "max": 2.0},
        }
    )

    assert entry.ref.parameter_id == "PRM1"
    assert entry.ref.data_template_id == ref.get("dataTemplateId")
    assert entry.ref.parameter_group_id == ref.get("parameterGroupId")
    assert entry.ref.unit_id == ref.get("unitId")


def test_ingredient_entry_rejects_a_fraction_outside_zero_to_one():
    """Test that a fraction bound outside [0, 1] fails validation."""
    with pytest.raises(ValidationError):
        DesignSpace.model_validate(
            {"ingredients": {"INV001": {"action": "mayInclude", "min": 0.5, "max": 1.5}}}
        )


def test_set_count_bounds_requires_at_least_one_bound():
    """Test that a count-bounds operation with no bound at all fails validation."""
    with pytest.raises(ValidationError, match="min_count or max_count"):
        SetCountBoundsOperation()


def test_set_count_bounds_keeps_an_explicit_null_for_serialization():
    """Test that an explicit null bound survives unset-field exclusion, meaning clear."""
    operation = SetCountBoundsOperation(min_count=None, max_count=4)

    assert operation.model_dump(by_alias=True, mode="json", exclude_unset=True) == {
        "op": "setCountBounds",
        "minCount": None,
        "maxCount": 4,
    }


def test_violation_parses_code_and_component_attribution():
    """Test that a violation carries its code, target, and attributed components."""
    violation = DesignSpaceViolation.model_validate(
        {
            "code": "unknown_reference",
            "message": "No such ingredient.",
            "targetId": "ingredients/INV999",
            "components": ["ingredients/INV999"],
        }
    )

    assert violation.code == "unknown_reference"
    assert violation.target_id == "ingredients/INV999"
    assert violation.components == ["ingredients/INV999"]


def test_violation_carries_the_operation_it_came_from():
    """Test that an apply finding keeps the position of the operation behind it."""
    violation = DesignSpaceViolation.model_validate(
        {"code": "unknown_reference", "message": "No such ingredient.", "opIndex": 2}
    )

    assert violation.op_index == 2
    assert (
        DesignSpaceViolation.model_validate({"code": "internal", "message": "m"}).op_index is None
    )


@pytest.mark.parametrize("code", ["variable_not_derived", "duplicate_constraint_subject"])
def test_violation_accepts_the_newer_warning_codes(code):
    """Test that codes the service can now return parse instead of failing validation."""
    assert DesignSpaceViolation.model_validate({"code": code, "message": "m"}).code == code


def test_violation_rejects_an_unknown_code():
    """Test that a violation code outside the known vocabulary fails validation."""
    with pytest.raises(ValidationError):
        DesignSpaceViolation.model_validate({"code": "surprise", "message": "m"})


def test_sample_and_references_preserve_undeclared_keys():
    """Test that the open-ended sample and reference documents keep unknown keys."""
    sample = DesignSpaceSample.model_validate({"rows": [{"INV001": 0.5}], "seed": 7})
    references = DesignSpaceReferences.model_validate({"references": []})

    assert sample.model_dump() == {"rows": [{"INV001": 0.5}], "seed": 7}
    assert references.model_dump() == {"references": []}
