import json
from pathlib import Path

import pytest

from albert.utils.calculations import validate_calculation_expression

_CORPUS_PATH = Path(__file__).with_name("calculation_expression_corpus.json")


def _load_corpus() -> dict:
    """Load the shared expression corpus mirrored from the platform engine."""
    with _CORPUS_PATH.open() as f:
        return json.load(f)


def _corpus_ids() -> list[str]:
    return [entry["rule"] if entry["platform"] == "rejected" else "accepted" for entry in _entries]


_corpus = _load_corpus()
_entries = _corpus["entries"]


def test_corpus_shape():
    """Test that the mirrored corpus carries the fields both consumers rely on."""
    assert _corpus["version"] == 1
    assert len(_entries) > 0
    for entry in _entries:
        assert isinstance(entry["expression"], str)
        assert entry["platform"] in ("accepted", "rejected")
        if entry["platform"] == "rejected":
            assert entry["stage"] in ("normalize", "evaluate")
            assert isinstance(entry["rule"], str)


@pytest.mark.parametrize(
    "entry",
    [pytest.param(entry, id=f"{entry['platform']}-{i}") for i, entry in enumerate(_entries)],
)
def test_validate_calculation_expression_matches_platform_verdict(entry):
    """Test that the SDK verdict matches the platform verdict for every corpus entry."""
    if entry["platform"] == "accepted":
        validate_calculation_expression(expression=entry["expression"])
    else:
        with pytest.raises(ValueError):
            validate_calculation_expression(expression=entry["expression"])


# --- SDK-only pass-through cases (not engine expressions, so not in the shared corpus) ---


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("=", id="bare-equals"),
        pytest.param("=COL5ROW12+COL6ROW12", id="column-references"),
        pytest.param("=((COL3-COL1)/COL2)*100", id="column-arithmetic"),
    ],
)
def test_validate_calculation_expression_passes_through_non_engine_expressions(expression):
    """Test that cell coordinate formulas and empty states pass unexamined."""
    validate_calculation_expression(expression=expression)


# --- Message content (the SDK owns its error text; the corpus owns the verdicts) ---


def test_validate_calculation_expression_and_error_points_to_or():
    """Test that an AND rejection explains the OR alternative."""
    expression = 'sum(wt% WHERE Function = "Core" AND Function = "Shell")'

    with pytest.raises(ValueError, match="AND conditions in WHERE filters are not supported"):
        validate_calculation_expression(expression=expression)


def test_validate_calculation_expression_rejects_mixed_keys():
    """Test that OR branches with different keys are rejected."""
    expression = 'sum(wt% WHERE Function = "Core" OR [Resin Type] = "Epoxy")'

    with pytest.raises(ValueError, match="mixes keys"):
        validate_calculation_expression(expression=expression)


def test_validate_calculation_expression_rejects_unmatched_parentheses():
    """Test that an unclosed sum(...) is rejected."""
    with pytest.raises(ValueError, match="Unmatched parentheses"):
        validate_calculation_expression(expression='sum(wt% WHERE Function = "Core"')


def test_validate_calculation_expression_rejects_malformed_condition():
    """Test that an unquoted WHERE value is rejected with the expected form."""
    with pytest.raises(ValueError, match="Unsupported WHERE condition"):
        validate_calculation_expression(expression="sum(wt% WHERE Function = Core)")
