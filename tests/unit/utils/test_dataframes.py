"""Unit tests for the tight-orient DataFrame (de)serialization helpers."""

from __future__ import annotations

import math

import pandas as pd
from pydantic import BaseModel, ConfigDict

from albert.utils.dataframes import OrientTightDataFrame, _deserialize_tight_dataframe


class _Wrapper(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame: OrientTightDataFrame


def _tight_payload() -> dict:
    return {
        "index": [0, 1],
        "columns": ["a", "b"],
        "data": [[1, "x"], [2, None]],
        "index_names": [None],
        "column_names": [None],
    }


def test_deserialize_tight_dataframe_passes_through_existing_dataframe():
    """Test that an already-constructed DataFrame is returned unchanged."""
    df = pd.DataFrame({"a": [1, 2]})

    result = _deserialize_tight_dataframe(df)

    assert result is df


def test_deserialize_tight_dataframe_builds_frame_from_tight_dict():
    """Test that a tight-orient dict is converted into the equivalent DataFrame."""
    result = _deserialize_tight_dataframe(_tight_payload())

    assert list(result.columns) == ["a", "b"]
    assert result["a"].tolist() == [1, 2]
    assert result["b"][0] == "x"


def test_deserialize_tight_dataframe_preserves_nan_for_object_columns():
    """Test that a JSON null in an object-dtype column becomes float NaN, not None."""
    result = _deserialize_tight_dataframe(_tight_payload())

    value = result["b"][1]
    assert isinstance(value, float)
    assert math.isnan(value)


def test_deserialize_tight_dataframe_leaves_numeric_columns_untouched():
    """Test that a fully-numeric column is unaffected by the NaN-preservation pass."""
    result = _deserialize_tight_dataframe(_tight_payload())

    assert result["a"].dtype.kind in "iu"


def test_orient_tight_dataframe_validates_a_tight_dict_into_a_dataframe():
    """Test that a pydantic field typed OrientTightDataFrame parses a tight dict."""
    wrapper = _Wrapper.model_validate({"frame": _tight_payload()})

    assert isinstance(wrapper.frame, pd.DataFrame)
    assert wrapper.frame["a"].tolist() == [1, 2]
    assert wrapper.frame["b"][0] == "x"


def test_orient_tight_dataframe_serializes_back_to_a_tight_dict():
    """Test that dumping the model serializes the DataFrame back to tight orient."""
    wrapper = _Wrapper.model_validate({"frame": _tight_payload()})

    dumped = wrapper.model_dump()

    assert dumped["frame"]["columns"] == ["a", "b"]
    assert dumped["frame"]["data"][0] == [1, "x"]
    assert math.isnan(dumped["frame"]["data"][1][1])
