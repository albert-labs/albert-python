import pytest

from albert.utils.calculations import validate_calculation_expression


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("=", id="bare-equals"),
        pytest.param("=COL5ROW12+COL6ROW12", id="column-references"),
        pytest.param("=((COL3-COL1)/COL2)*100", id="column-arithmetic"),
        pytest.param("wt% * [Solid %] / 100", id="plain-ingredient-expression"),
        pytest.param("parts_mass / [Density]", id="parts-mass-expression"),
        pytest.param("sum(wt%)", id="sum-all-ingredients"),
        pytest.param('sum(wt% WHERE Function = "Core")', id="where-function"),
        pytest.param('sum(wt% where Function = "Core")', id="where-lowercase"),
        pytest.param('sum(wt% WHERE Function="Core")', id="where-tight-equals"),
        pytest.param(
            'sum(wt% WHERE Function = "Core" OR Function = "Shell")', id="where-or-two-values"
        ),
        pytest.param(
            'sum(wt% WHERE Function = "Core" OR Function = "Core")', id="where-or-duplicate-values"
        ),
        pytest.param("sum(parts_mass WHERE [Resin Type] = 'Epoxy')", id="where-bracketed-key"),
        pytest.param('sum(wt% WHERE [ATR66] = "Resin")', id="where-attribute-id-key"),
        pytest.param('wt% / sum(wt% WHERE Function = "Resin") * 100', id="phr-share-of-sum"),
        pytest.param('sum(wt% * [Solid %] / 100 WHERE Function = "Resin")', id="where-on-product"),
        pytest.param("sum(wt%) + sum(parts_mass)", id="two-sibling-sums"),
        pytest.param("harmonicMean(wt%, [Density])", id="harmonic-mean"),
    ],
)
def test_validate_calculation_expression_accepts(expression):
    """Test that well-formed expressions pass validation."""
    validate_calculation_expression(expression=expression)


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("sum(wt%", id="unmatched-open-paren"),
        pytest.param('sum(wt% WHERE Function = "Core"', id="unmatched-open-paren-with-where"),
    ],
)
def test_validate_calculation_expression_rejects_unmatched_parentheses(expression):
    """Test that an unclosed sum(...) is rejected."""
    with pytest.raises(ValueError, match="Unmatched parentheses"):
        validate_calculation_expression(expression=expression)


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param('sum(wt% WHERE Function = "Core" AND Function = "Shell")', id="and-in-where"),
        pytest.param('sum(wt% WHERE Function = "Core" and [Solid %] = "50")', id="and-lowercase"),
    ],
)
def test_validate_calculation_expression_rejects_and_conditions(expression):
    """Test that AND in a WHERE filter is rejected with guidance toward OR."""
    with pytest.raises(ValueError, match="AND conditions in WHERE filters are not supported"):
        validate_calculation_expression(expression=expression)


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("sum(wt% WHERE Function = Core)", id="unquoted-value"),
        pytest.param("sum(wt% WHERE Function)", id="missing-equals-and-value"),
        pytest.param('sum(wt% WHERE = "Core")', id="missing-key"),
        pytest.param('sum(wt% WHERE Function = "")', id="empty-value"),
        pytest.param("sum(wt% WHERE wt% > 50)", id="non-equals-operator"),
        pytest.param('sum(wt% WHERE Function = "Resin or Binder")', id="value-contains-or-word"),
    ],
)
def test_validate_calculation_expression_rejects_malformed_conditions(expression):
    """Test that a WHERE condition not in key = "value" form is rejected."""
    with pytest.raises(ValueError, match="Unsupported WHERE condition"):
        validate_calculation_expression(expression=expression)


def test_validate_calculation_expression_rejects_mixed_keys():
    """Test that OR branches with different keys are rejected."""
    expression = 'sum(wt% WHERE Function = "Core" OR [Resin Type] = "Epoxy")'

    with pytest.raises(ValueError, match="mixes keys"):
        validate_calculation_expression(expression=expression)


def test_validate_calculation_expression_rejects_missing_inner_expression():
    """Test that a WHERE filter with no expression to sum is rejected."""
    expression = 'sum(WHERE Function = "Core")'

    with pytest.raises(ValueError, match="Missing expression before the WHERE filter"):
        validate_calculation_expression(expression=expression)


def test_validate_calculation_expression_rejects_incomplete_where():
    """Test that a WHERE keyword without a full condition is rejected."""
    expression = "sum(wt% WHERE)"

    with pytest.raises(ValueError, match="Unsupported WHERE filter"):
        validate_calculation_expression(expression=expression)
