"""Unit tests for design-run request shaping."""

import pytest

from albert.resources.design import (
    DesignMethod,
    DesignRunSettings,
    SpaceFillingRunSettings,
)
from albert.resources.targets import ComparisonOperator, Criterion


def test_generate_request_body_unchanged() -> None:
    from albert.collections.design_runs import _build_design_run_request

    body = _build_design_run_request(
        smart_dataset_id="SDT1",
        objectives={
            "TAR1": Criterion(operator=ComparisonOperator.GTE, value=1.0),
        },
        method=DesignMethod.GENERATE,
        settings=DesignRunSettings(num_candidates_generated=1000, num_candidates_selected=5),
    )
    assert body == {
        "smartDatasetId": "SDT1",
        "method": "generate",
        "objectives": {"TAR1": {"operator": "gte", "value": 1.0}},
        "settings": {
            "numCandidatesGenerated": 1000,
            "numCandidatesSelected": 5,
        },
    }


def test_space_filling_request_serializes_camel_case() -> None:
    from albert.collections.design_runs import _build_design_run_request

    body = _build_design_run_request(
        smart_dataset_id="SDT1",
        method=DesignMethod.SPACE_FILLING,
        settings=SpaceFillingRunSettings(
            num_proposals=12,
            num_samples_per_dimension=5,
            max_num_polytopes=3,
            max_num_samples=100,
        ),
        anchor_targets=["TAR1"],
    )
    assert body == {
        "smartDatasetId": "SDT1",
        "method": "space_filling",
        "settings": {
            "numProposals": 12,
            "numSamplesPerDimension": 5,
            "maxNumPolytopes": 3,
            "maxNumSamples": 100,
        },
        "anchorTargets": ["TAR1"],
    }


def test_space_filling_rejects_objectives_client_side() -> None:
    from albert.collections.design_runs import DesignRunCollection

    with pytest.raises(ValueError, match="objectives"):
        DesignRunCollection._validate_create_args(
            method=DesignMethod.SPACE_FILLING,
            objectives={"TAR1": {"operator": "gte", "value": 1.0}},
            settings=None,
            anchor_targets=None,
        )


def test_generate_rejects_anchor_targets_client_side() -> None:
    from albert.collections.design_runs import DesignRunCollection

    with pytest.raises(ValueError, match="anchor_targets"):
        DesignRunCollection._validate_create_args(
            method=DesignMethod.GENERATE,
            objectives=None,
            settings=None,
            anchor_targets=["TAR1"],
        )


def test_space_filling_rejects_generate_settings_client_side() -> None:
    from albert.collections.design_runs import DesignRunCollection

    with pytest.raises(ValueError, match="settings"):
        DesignRunCollection._validate_create_args(
            method=DesignMethod.SPACE_FILLING,
            objectives=None,
            settings=DesignRunSettings(num_candidates_generated=10),
            anchor_targets=None,
        )
