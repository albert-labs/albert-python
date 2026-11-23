"""Unit tests for the design-space resource models: wire round-trips and validators."""

import pytest
from pydantic import ValidationError

from albert.resources.design_operands import (
    ConstantOperand,
    IngredientAmountOperand,
    LabelCountOperand,
    LinearTerm,
    PriceAggregationOperand,
    PropertyAggregation,
    PropertyAggregationOperand,
    UnknownConstraintOperand,
)
from albert.resources.design_spaces import (
    CategoricalConstraint,
    ContinuousConstraint,
    CreateDesignSpaceRequest,
    DesignSpace,
    DesignSpaceOperationsRequest,
    DesignSpaceReferences,
    DesignSpaceSample,
    DesignSpaceViolation,
    DesignSpaceViolationCode,
    DiscreteConstraint,
    IngredientEntry,
    LabelConstraint,
    LabelDefinition,
    LinearCombinationConstraint,
    ParameterAssignment,
    ParameterEntry,
    PriceConstraint,
    PropertyConstraint,
    PropertyRatioConstraint,
    RatioConstraint,
    RatioSide,
    SetConstraintOperation,
    SetCountBoundsOperation,
    SetIngredientOperation,
    SetLabelOperation,
    SetParameterOperation,
    UnknownDesignSpaceConstraint,
    UnknownParameterConstraint,
    UpdateComponentOperation,
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


def _apply_body(operation) -> dict:
    """Serialize one operation the way ``apply`` sends it."""
    request = DesignSpaceOperationsRequest(operations=[operation])
    return request.model_dump(by_alias=True, mode="json", exclude_unset=True)["operations"][0]


_CONSTRAINTS = [
    pytest.param(ContinuousConstraint(min=1.0, max=2.0), "numeric", "continuous", id="continuous"),
    pytest.param(DiscreteConstraint(values=[1.0, 2.0]), "numeric", "discrete", id="discrete"),
    pytest.param(
        CategoricalConstraint(values=["a", "b"]), "categorical", "categorical", id="categorical"
    ),
]


@pytest.mark.parametrize(("constraint", "data_type", "expected_type"), _CONSTRAINTS)
def test_set_parameter_sends_the_constraint_type_when_it_was_left_to_default(
    constraint, data_type, expected_type
):
    """Test that a constraint built without an explicit type still serializes its type."""
    operation = SetParameterOperation(
        parameter_id="PRM1",
        data_template_id="DAT1",
        parameter_group_id=None,
        unit_id=None,
        value=ParameterAssignment(data_type=data_type, constraint=constraint),
    )

    sent = _apply_body(operation)["value"]["constraint"]

    assert sent["type"] == expected_type
    assert sent == {
        "type": expected_type,
        **constraint.model_dump(exclude={"type"}, exclude_none=True),
    }


@pytest.mark.parametrize(("constraint", "data_type", "expected_type"), _CONSTRAINTS)
def test_update_component_sends_a_typed_constraint_value_with_its_type(
    constraint, data_type, expected_type
):
    """Test that a constraint object passed as an update value keeps its type on the wire."""
    operation = UpdateComponentOperation(
        path="parameters/DAT1#PRM1", field="constraint", value=constraint
    )

    assert _apply_body(operation)["value"]["type"] == expected_type


def test_a_constraint_still_validates_from_its_serialized_form():
    """Test that the always-serialized type does not break reading a constraint back."""
    constraint = ContinuousConstraint(min=1.0, max=2.0)

    assert ContinuousConstraint.model_validate(constraint.model_dump()) == constraint


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


@pytest.mark.parametrize(
    "code", ["variable_not_derived", "duplicate_constraint_subject", "unsupported_operand"]
)
def test_violation_accepts_the_newer_codes(code):
    """Test that codes the service can now return parse to the enum."""
    parsed = DesignSpaceViolation.model_validate({"code": code, "message": "m"}).code

    assert isinstance(parsed, DesignSpaceViolationCode)
    assert parsed == code


def test_violation_keeps_an_unknown_code_as_a_string():
    """Test that a code this version does not know yet parses instead of failing."""
    violation = DesignSpaceViolation.model_validate({"code": "brand_new_code", "message": "m"})

    assert violation.code == "brand_new_code"


def test_sample_and_references_preserve_undeclared_keys():
    """Test that the open-ended sample and reference documents keep unknown keys."""
    sample = DesignSpaceSample.model_validate({"rows": [{"INV001": 0.5}], "seed": 7})
    references = DesignSpaceReferences.model_validate({"references": [], "newField": 1})

    assert sample.model_dump() == {"rows": [{"INV001": 0.5}], "seed": 7}
    assert references.references == []
    assert references.model_dump() == {"references": [], "newField": 1}


# No explicit nulls, so the read round-trips under ``exclude_none``.
_REF = {"parameterId": "PRM07", "dataTemplateId": "DAT01"}

_NEWER_SPACE = {
    "id": "DSP123",
    "name": "Low-VOC clearcoat envelope",
    "parentId": "PRO456",
    "state": "draft",
    "parameters": {
        "DAT01#PRM07": {
            "ref": _REF,
            "dataType": "numeric",
            "constraint": {"type": "continuous", "min": 60, "max": 120, "newField": 5},
            "otherField": "x",
        },
        "DAT01#PRM08": {
            "ref": {**_REF, "parameterId": "PRM08"},
            "dataType": "numeric",
            "constraint": {"type": "newKind", "min": 1, "max": 1000},
        },
    },
    "newCollection": {"X1": {"type": "newKind"}},
    "newNote": "y",
}


def test_a_newer_space_parses_and_keeps_what_this_version_does_not_model():
    """Test that unknown fields, constraint kinds and constraint fields survive a read."""
    space = DesignSpace.model_validate(_NEWER_SPACE)

    known = space.parameters["DAT01#PRM07"]
    assert isinstance(known.constraint, ContinuousConstraint)
    assert known.model_extra == {"otherField": "x"}
    unknown = space.parameters["DAT01#PRM08"].constraint
    assert isinstance(unknown, UnknownParameterConstraint)
    assert unknown.type == "newKind"
    assert set(space.model_extra) == {"newCollection", "newNote"}
    assert space.model_dump(by_alias=True, mode="json", exclude_none=True) == _NEWER_SPACE


def test_a_space_that_carries_only_albert_id_reads_it_as_the_id():
    """Test that the ID is read from ``albertId`` when ``id`` is absent, and kept once."""
    space = DesignSpace.model_validate({"albertId": "DSP123", "name": "n"})

    assert space.id == "DSP123"
    assert "albertId" not in space.model_extra


def test_requests_still_reject_constraint_kinds_and_fields_the_service_does_not_accept():
    """Test that only reads are lenient: a parameter assignment keeps the strict schema."""
    with pytest.raises(ValidationError):
        ParameterAssignment.model_validate(
            {"dataType": "numeric", "constraint": {"type": "newKind", "min": 1, "max": 9}}
        )
    with pytest.raises(ValidationError):
        ParameterAssignment.model_validate(
            {"dataType": "numeric", "constraint": {"type": "continuous", "min": 1, "newField": 5}}
        )


def test_a_read_constraint_is_checked_again_when_sent():
    """Test that a constraint read from a space is refused in a request if it carries more."""
    space = DesignSpace.model_validate(
        {
            "id": "DSP1",
            "parameters": {
                "DAT01#PRM07": {
                    "ref": _REF,
                    "dataType": "numeric",
                    "constraint": {"type": "continuous", "min": 1, "max": 2, "newField": 3},
                },
                "DAT01#PRM08": {
                    "ref": {**_REF, "parameterId": "PRM08"},
                    "dataType": "numeric",
                    "constraint": {"type": "continuous", "min": 1, "max": 2},
                },
            },
        }
    )

    known = ParameterAssignment(
        data_type="numeric", constraint=space.parameters["DAT01#PRM08"].constraint
    )
    assert known.model_dump(by_alias=True, mode="json", exclude_none=True)["constraint"] == {
        "type": "continuous",
        "min": 1.0,
        "max": 2.0,
    }
    with pytest.raises(ValidationError):
        ParameterAssignment(
            data_type="numeric", constraint=space.parameters["DAT01#PRM07"].constraint
        )


def test_a_malformed_constraint_of_a_known_kind_raises():
    """Test that a known constraint kind that breaks its schema fails, rather than reading as unknown."""
    with pytest.raises(ValidationError):
        ParameterEntry.model_validate(
            {"ref": _REF, "dataType": "numeric", "constraint": {"type": "discrete", "values": []}}
        )


_BETA_SPACE = {
    "id": "DSP123",
    "name": "Beta clearcoat",
    "parentId": "PRO456",
    "state": "draft",
    "ingredients": {
        "INV001": {"action": "mustInclude", "min": 0.4, "max": 0.65, "rationale": "resin"},
    },
    "labels": {"local:additives": {"name": "Additives", "members": ["INV004", "INV005"]}},
    "constraints": {
        "CONLB001": {
            "type": "label",
            "label": "TAG42",
            "action": "mayInclude",
            "maxFraction": 0.35,
        },
        "CONRT001": {
            "type": "ratio",
            "numerator": {"ingredient": "INV001"},
            "denominator": {"label": "local:additives"},
            "constant": 1.0,
            "min": 1.5,
            "max": 2.5,
            "rationale": "stoichiometry",
        },
        "CONPR001": {
            "type": "property",
            "aggregation": {"basis": "mean", "property": "Tg", "useReciprocal": True},
            "min": 40.0,
        },
        "CONPT001": {
            "type": "propertyRatio",
            "numerator": {"basis": "sum", "property": "OH"},
            "denominator": {"basis": "sum", "property": "NCO", "label": "local:additives"},
            "constant": 1.0,
            "max": 1.1,
        },
        "CONPC001": {"type": "price", "impute": True, "max": 4.5},
        "CONLC001": {
            "type": "linearCombination",
            "name": "additive budget",
            "terms": [
                {
                    "coefficient": 1.0,
                    "operand": {"type": "ingredientAmount", "ingredient": "INV004"},
                },
                {
                    "coefficient": 2.0,
                    "operand": {"type": "labelCount", "label": "local:additives"},
                },
                {
                    "coefficient": 0.5,
                    "operand": {"type": "priceAggregation", "basis": "sum", "impute": 3.0},
                },
                {"coefficient": 1.0, "operand": {"type": "constant", "value": -0.01}},
            ],
            "max": 0.04,
        },
    },
    "componentIndex": {
        "INV004": ["labels/local:additives", "constraints/CONLC001"],
        "local:additives": ["labels/local:additives", "constraints/CONRT001"],
    },
}


def test_a_beta_space_round_trips_every_constraint_kind_unchanged():
    """Test that labels, each constraint kind, componentIndex and rationale round-trip."""
    space = DesignSpace.model_validate(_BETA_SPACE)

    assert space.model_dump(by_alias=True, mode="json", exclude_none=True) == _BETA_SPACE


@pytest.mark.parametrize(
    ("key", "model"),
    [
        ("CONLB001", LabelConstraint),
        ("CONRT001", RatioConstraint),
        ("CONPR001", PropertyConstraint),
        ("CONPT001", PropertyRatioConstraint),
        ("CONPC001", PriceConstraint),
        ("CONLC001", LinearCombinationConstraint),
    ],
)
def test_a_read_constraint_parses_to_its_kind(key, model):
    """Test that each stored constraint parses to the model of its kind."""
    space = DesignSpace.model_validate(_BETA_SPACE)

    assert isinstance(space.constraints[key], model)


def test_a_beta_space_keeps_local_label_keys_and_parses_typed_operands():
    """Test that local: keys stay as written and weighted-sum operands parse to their kinds."""
    space = DesignSpace.model_validate(_BETA_SPACE)

    assert list(space.labels) == ["local:additives"]
    assert space.labels["local:additives"].members == ["INV004", "INV005"]
    operands = [term.operand for term in space.constraints["CONLC001"].terms]
    assert [type(o).__mro__[1] for o in operands] == [
        IngredientAmountOperand,
        LabelCountOperand,
        PriceAggregationOperand,
        ConstantOperand,
    ]
    assert space.component_index["local:additives"] == [
        "labels/local:additives",
        "constraints/CONRT001",
    ]


def test_an_alpha_space_reads_with_no_beta_collections():
    """Test that a space written before beta parses with the beta fields left empty."""
    space = DesignSpace.model_validate({"id": "DSP1", "ingredients": {}, "parameters": {}})

    assert (space.labels, space.constraints, space.component_index) == (None, None, None)
    assert space.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        "id": "DSP1",
        "ingredients": {},
        "parameters": {},
    }


def test_a_newer_constraint_kind_and_fields_survive_a_read():
    """Test that an unknown constraint kind, operand kind and extra fields are kept."""
    wire = {
        "id": "DSP1",
        "labels": {"local:a": {"name": "A", "members": [], "color": "red"}},
        "constraints": {
            "CONXX001": {"type": "conditional", "when": {"x": 1}},
            "CONLB001": {"type": "label", "label": "local:a", "action": "exclude", "newField": 2},
            "CONLC001": {
                "type": "linearCombination",
                "terms": [{"coefficient": 1.0, "operand": {"type": "newOperand", "x": 1}}],
            },
        },
    }

    space = DesignSpace.model_validate(wire)

    assert isinstance(space.constraints["CONXX001"], UnknownDesignSpaceConstraint)
    assert space.constraints["CONLB001"].model_extra == {"newField": 2}
    assert isinstance(space.constraints["CONLC001"].terms[0].operand, UnknownConstraintOperand)
    assert space.model_dump(by_alias=True, mode="json", exclude_none=True) == wire


def test_a_malformed_constraint_of_a_known_kind_raises_on_read():
    """Test that a known constraint kind that breaks its schema fails, not reads as unknown."""
    with pytest.raises(ValidationError):
        DesignSpace.model_validate(
            {"constraints": {"CONLB001": {"type": "label", "action": "mayInclude"}}}
        )


def test_beta_operations_serialize_with_their_op_and_type_discriminators():
    """Test that setLabel and setConstraint keep op and every nested type when sent."""
    request = DesignSpaceOperationsRequest(
        operations=[
            SetIngredientOperation(
                key="INV001", value=IngredientEntry(action="mayInclude", rationale="r")
            ),
            SetLabelOperation(
                key="local:thickeners",
                value=LabelDefinition(name="Thickeners", members=["INV001"]),
            ),
            SetConstraintOperation(
                value=LabelConstraint(label="local:thickeners", action="mustInclude", min_count=2)
            ),
            SetConstraintOperation(
                key="CONLC001",
                value=LinearCombinationConstraint(
                    terms=[
                        LinearTerm(
                            coefficient=1,
                            operand=PropertyAggregationOperand(basis="sum", property="Tg"),
                        )
                    ],
                    max=1,
                ),
            ),
            SetConstraintOperation(
                value=PropertyConstraint(
                    aggregation=PropertyAggregation(
                        basis="mean", property="Tg", use_reciprocal=True
                    )
                )
            ),
        ]
    )

    assert request.model_dump(by_alias=True, mode="json", exclude_unset=True)["operations"] == [
        {
            "op": "setIngredient",
            "key": "INV001",
            "value": {"action": "mayInclude", "rationale": "r"},
        },
        {
            "op": "setLabel",
            "key": "local:thickeners",
            "value": {"name": "Thickeners", "members": ["INV001"]},
        },
        {
            "op": "setConstraint",
            "value": {
                "type": "label",
                "label": "local:thickeners",
                "action": "mustInclude",
                "minCount": 2,
            },
        },
        {
            "op": "setConstraint",
            "key": "CONLC001",
            "value": {
                "type": "linearCombination",
                "terms": [
                    {
                        "coefficient": 1.0,
                        "operand": {
                            "type": "propertyAggregation",
                            "basis": "sum",
                            "property": "Tg",
                        },
                    }
                ],
                "max": 1.0,
            },
        },
        {
            "op": "setConstraint",
            "value": {
                "type": "property",
                "aggregation": {"basis": "mean", "property": "Tg", "useReciprocal": True},
            },
        },
    ]


@pytest.mark.parametrize(
    "operation",
    [
        {"op": "setLabel", "key": "TAG42", "value": {"name": "A", "members": []}},
        {"op": "setLabel", "key": "local:", "value": {"name": "A", "members": []}},
        {"op": "setLabel", "key": "local:a", "value": {"name": "", "members": []}},
        {"op": "setLabel", "key": "local:a", "value": {"name": "A", "members": [], "x": 1}},
        {"op": "setConstraint", "value": {"type": "conditional"}},
        {"op": "setConstraint", "value": {"type": "label", "label": "TAG1", "action": "x"}},
        {
            "op": "setConstraint",
            "value": {"type": "label", "label": "TAG1", "action": "exclude", "maxFraction": 2},
        },
        {
            "op": "setConstraint",
            "value": {"type": "label", "label": "TAG1", "action": "exclude", "newField": 1},
        },
        {"op": "setConstraint", "value": {"type": "linearCombination", "terms": []}},
        {"op": "setConstraint", "key": "", "value": {"type": "price"}},
    ],
)
def test_beta_operations_reject_what_the_service_does_not_accept(operation):
    """Test that malformed label and constraint operations fail before anything is sent."""
    with pytest.raises(ValidationError):
        DesignSpaceOperationsRequest.model_validate({"operations": [operation]})


@pytest.mark.parametrize(
    "side",
    [{}, {"ingredient": "INV001", "label": "TAG1"}],
)
def test_a_ratio_side_needs_exactly_one_of_ingredient_or_label(side):
    """Test that a ratio side with neither or both of ingredient and label is rejected."""
    with pytest.raises(ValidationError):
        RatioSide.model_validate(side)


def test_a_read_design_space_constraint_is_checked_again_when_sent():
    """Test that a read constraint resends when known-only and is refused when it carries more."""
    known = {"type": "label", "label": "local:a", "action": "exclude", "maxFraction": 0.2}
    space = DesignSpace.model_validate(
        {"constraints": {"CONLB001": known, "CONLB002": {**known, "newField": 1}}}
    )

    resent = SetConstraintOperation(key="CONLB001", value=space.constraints["CONLB001"])
    assert resent.model_dump(by_alias=True, mode="json", exclude_unset=True)["value"] == known
    with pytest.raises(ValidationError):
        SetConstraintOperation(key="CONLB002", value=space.constraints["CONLB002"])


def test_the_empty_label_warning_parses_as_a_known_code():
    """Test that the empty_label warning code parses to its enum member."""
    violation = DesignSpaceViolation.model_validate(
        {"code": "empty_label", "message": "m", "components": ["labels/local:a"]}
    )

    assert violation.code is DesignSpaceViolationCode.EMPTY_LABEL
