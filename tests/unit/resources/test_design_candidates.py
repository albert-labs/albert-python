"""Unit tests for the design candidate and candidate-set resource models."""

from albert.resources.design_candidate_sets import CandidateSetSourceType, DesignCandidateSet
from albert.resources.design_candidates import (
    DesignCandidate,
    IngredientAmountInput,
    ParameterInput,
    PredictionDataType,
)
from albert.resources.design_operands import UnknownDescriptor

CANDIDATE = {
    "id": "DCN1",
    "candidateSetId": "DCS2201",
    "parentId": "PRO456",
    "inputs": [
        {"type": "ingredientAmount", "ingredient": "INV001", "value": 0.0},
        {
            "type": "parameter",
            "parameter": "DAT01#PRM07#UNI12",
            "ref": {
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": "UNI12",
            },
            "value": "cured",
        },
    ],
    "predictions": {
        "TAR1": {
            "value": 96.5,
            "uncertainty": 1.2,
            "dataType": "numeric",
            "quantiles": {"levels": [0.1, 0.9], "values": [95.0, 98.0]},
        },
        "TAR2": {"value": "pass", "uncertainty": 0.4, "dataType": "categorical"},
    },
    "acquisition": {"score": 0.8, "perObjective": {"TAR1": 0.8}},
    "rank": 1,
}


def test_candidate_inputs_dispatch_on_type():
    """Test that each input parses to its own kind, a zero amount and an explicit null kept."""
    candidate = DesignCandidate.model_validate(CANDIDATE)

    amount, parameter = candidate.inputs
    assert isinstance(amount, IngredientAmountInput)
    assert amount.value == 0.0
    assert isinstance(parameter, ParameterInput)
    assert parameter.ref.data_template_id == "DAT01"
    assert parameter.ref.parameter_group_id is None
    assert parameter.value == "cured"


def test_candidate_predictions_parse_numeric_and_categorical_outputs():
    """Test that a quantile prediction and a categorical mode both parse."""
    predictions = DesignCandidate.model_validate(CANDIDATE).predictions

    assert predictions["TAR1"].data_type == PredictionDataType.NUMERIC
    assert predictions["TAR1"].quantiles.levels == [0.1, 0.9]
    assert predictions["TAR2"].data_type == PredictionDataType.CATEGORICAL
    assert predictions["TAR2"].value == "pass"


def test_sampling_candidate_without_predictions_or_acquisition_parses():
    """Test that a space-filling candidate, read by id with no rank, parses."""
    sampling = {
        k: v for k, v in CANDIDATE.items() if k not in {"predictions", "acquisition", "rank"}
    }

    candidate = DesignCandidate.model_validate(sampling)

    assert candidate.predictions is None
    assert candidate.acquisition is None
    assert candidate.rank is None


def test_acquisition_without_per_objective_scores_parses():
    """Test that an acquisition carrying only the overall score parses."""
    candidate = DesignCandidate.model_validate({**CANDIDATE, "acquisition": {"score": 0.5}})

    assert candidate.acquisition.per_objective is None


def test_candidate_set_parses_its_source():
    """Test that a run-produced set names the run as its source."""
    candidate_set = DesignCandidateSet.model_validate(
        {
            "id": "DCS2201",
            "parentId": "PRO456",
            "source": {"sourceType": "design_run", "sourceId": "DSR1042"},
            "smartDatasetId": "SDT789",
            "objectives": {"TAR1": {"operator": "gte", "value": 95}},
        }
    )

    assert candidate_set.source.source_type == CandidateSetSourceType.DESIGN_RUN
    assert candidate_set.source.source_id == "DSR1042"
    assert candidate_set.objectives["TAR1"].weight == 1.0


def test_candidate_inputs_keep_fields_and_kinds_this_version_does_not_model():
    """Test that a newer descriptor field or input kind reads instead of failing."""
    candidate = DesignCandidate.model_validate(
        {
            **CANDIDATE,
            "inputs": [
                {
                    "type": "ingredientAmount",
                    "ingredient": "INV001",
                    "value": 0.2,
                    "newField": "x",
                },
                {"type": "newKind", "key": "X1", "value": 3},
            ],
        }
    )

    amount, unknown = candidate.inputs
    assert isinstance(amount, IngredientAmountInput)
    assert amount.model_extra == {"newField": "x"}
    assert isinstance(unknown, UnknownDescriptor)
    assert unknown.model_dump(mode="json") == {"type": "newKind", "key": "X1", "value": 3}
