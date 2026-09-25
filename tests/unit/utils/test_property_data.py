"""Unit tests for task property data utility functions."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pandas as pd
import pytest

from albert.core.shared.models.patch import PatchOperation
from albert.resources.property_data import (
    DataInterval,
    PropertyData,
    PropertyDataInventoryInformation,
    PropertyValue,
    TaskDataColumn,
    TaskPropertyCreate,
    TaskPropertyData,
    Trial,
)
from albert.resources.tasks import Block, PropertyTask
from albert.resources.workflows import (
    Interval,
    IntervalCombination,
    ParameterGroupSetpoints,
    ParameterSetpoint,
    Workflow,
)
from albert.utils.property_data import (
    _df_to_task_prop_create_list,
    _get_column_map,
    _safe_eval_math,
    _setpoint_display_value,
    build_interval_setpoint_map,
    evaluate_calculation,
    flatten_task_property_data,
    form_calculated_task_property_patches,
    generate_data_patch_payload,
    get_all_columns_used_in_calculations,
    get_columns_used_in_calculation,
    get_on_platform_row,
    map_block_final_workflows,
    prepare_new_task_property,
    resolve_data_template_id,
    resolve_return_scope,
    resolve_trial_number,
    trial_has_recorded_data,
)

# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------


def _property_data(columns: list[PropertyValue], *, trial_number: int = 1) -> TaskPropertyData:
    """Build a minimal TaskPropertyData with one interval/trial holding ``columns``."""
    trial = Trial(trial_number=trial_number, data_columns=columns)
    interval = DataInterval(interval_combination="default", trials=[trial])
    return TaskPropertyData(parent_id="TAS1", data=[interval])


def _make_prop(
    *, trial_number: int | None = None, interval: str = "default"
) -> TaskPropertyCreate:
    kwargs = {
        "data_column": TaskDataColumn(data_column_id="DAC1"),
        "value": "1",
        "interval_combination": interval,
    }
    if trial_number is not None:
        kwargs["trial_number"] = trial_number
    return TaskPropertyCreate(**kwargs)


def _existing_with_visible_trials(entries: list[tuple[int, int]]) -> TaskPropertyData:
    trials = [Trial(trial_number=t, visible_trial_number=v) for t, v in entries]
    interval = DataInterval(interval_combination="default", trials=trials)
    return TaskPropertyData(parent_id="TAS1", data=[interval])


def _existing_rows_with_calc(*, col_a_value: str = "10", col_b_value: str | None = "15"):
    """One trial with a source column (COL1) and a dependent column (COL2 = COL1*2)."""
    col_a = PropertyValue(
        name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value=col_a_value)
    )
    col_b = PropertyValue(
        name="B",
        sequence="COL2",
        calculation="=COL1*2",
        property_data=PropertyData(id="PTD2", value=col_b_value),
    )
    trial = Trial(trial_number=1, data_columns=[col_a, col_b])
    interval = DataInterval(interval_combination="default", trials=[trial])
    return TaskPropertyData(parent_id="TAS1", data=[interval])


# ---------------------------------------------------------------------------
# resolve_return_scope
# ---------------------------------------------------------------------------


def test_resolve_return_scope_task_delegates_to_get_all():
    """Test that scope 'task' returns all task properties without touching the block getter."""
    calls = []

    def get_all(*, task_id):
        calls.append(task_id)
        return ["ALL"]

    def get_block(**kwargs):
        raise AssertionError("get_task_block_properties should not be called")

    result = resolve_return_scope(
        task_id="TAS1",
        return_scope="task",
        inventory_id=None,
        block_id=None,
        lot_id=None,
        prefetched_block=None,
        get_all_task_properties=get_all,
        get_task_block_properties=get_block,
    )

    assert result == ["ALL"]
    assert calls == ["TAS1"]


def test_resolve_return_scope_block_uses_prefetched_block_without_fetching():
    """Test that a prefetched block is returned as-is without an extra fetch."""
    result = resolve_return_scope(
        task_id="TAS1",
        return_scope="block",
        inventory_id=None,
        block_id=None,
        lot_id=None,
        prefetched_block="PREFETCHED",
        get_all_task_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
        get_task_block_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
    )

    assert result == ["PREFETCHED"]


def test_resolve_return_scope_block_fetches_when_not_prefetched():
    """Test that scope 'block' fetches via the block getter when nothing is prefetched."""

    def get_block(*, inventory_id, task_id, block_id, lot_id):
        return f"{inventory_id}-{task_id}-{block_id}-{lot_id}"

    result = resolve_return_scope(
        task_id="TAS1",
        return_scope="block",
        inventory_id="INV1",
        block_id="BLK1",
        lot_id="LOT1",
        prefetched_block=None,
        get_all_task_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
        get_task_block_properties=get_block,
    )

    assert result == ["INV1-TAS1-BLK1-LOT1"]


def test_resolve_return_scope_block_requires_inventory_and_block_id():
    """Test that scope 'block' without a prefetch and missing ids raises ValueError."""
    with pytest.raises(ValueError, match="inventory_id and block_id are required"):
        resolve_return_scope(
            task_id="TAS1",
            return_scope="block",
            inventory_id=None,
            block_id=None,
            lot_id=None,
            prefetched_block=None,
            get_all_task_properties=lambda **_: [],
            get_task_block_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
        )


@pytest.mark.xfail(
    strict=True,
    reason="BUG: property_data.py:81 error message says return_scope='combo' but the "
    "check guards return_scope=='block'; message should name the actual scope.",
)
def test_resolve_return_scope_block_error_message_names_block_scope():
    """Test that the missing-ids error message names the 'block' scope it actually guards."""
    with pytest.raises(ValueError, match="return_scope='block'"):
        resolve_return_scope(
            task_id="TAS1",
            return_scope="block",
            inventory_id=None,
            block_id=None,
            lot_id=None,
            prefetched_block=None,
            get_all_task_properties=lambda **_: [],
            get_task_block_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
        )


def test_resolve_return_scope_none_returns_empty_list():
    """Test that scope 'none' returns an empty list without calling either getter."""
    result = resolve_return_scope(
        task_id="TAS1",
        return_scope="none",
        inventory_id=None,
        block_id=None,
        lot_id=None,
        prefetched_block=None,
        get_all_task_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
        get_task_block_properties=lambda **_: (_ for _ in ()).throw(AssertionError()),
    )

    assert result == []


# ---------------------------------------------------------------------------
# resolve_data_template_id
# ---------------------------------------------------------------------------


def test_resolve_data_template_id_reads_id_from_object():
    """Test extracting the data template id from an object with an id attribute."""
    prop = TaskPropertyCreate.model_construct(data_template=SimpleNamespace(id="DAT1"))

    assert resolve_data_template_id(prop=prop) == "DAT1"


def test_resolve_data_template_id_reads_id_from_dict():
    """Test extracting the data template id from a dict using the 'id' key."""
    prop = TaskPropertyCreate.model_construct(data_template={"id": "DAT2"})

    assert resolve_data_template_id(prop=prop) == "DAT2"


def test_resolve_data_template_id_falls_back_to_albert_id_key():
    """Test that a dict without 'id' falls back to the 'albertId' key."""
    prop = TaskPropertyCreate.model_construct(data_template={"albertId": "DAT3"})

    assert resolve_data_template_id(prop=prop) == "DAT3"


def test_resolve_data_template_id_raises_when_missing():
    """Test that a missing data_template raises ValueError."""
    prop = TaskPropertyCreate.model_construct(data_template=None)

    with pytest.raises(ValueError, match="data_template is required"):
        resolve_data_template_id(prop=prop)


# ---------------------------------------------------------------------------
# _get_column_map
# ---------------------------------------------------------------------------


def test_get_column_map_maps_dataframe_columns_to_property_values():
    """Test that each dataframe column maps to its single matching property value."""
    columns = [
        PropertyValue(name="Viscosity", id="DAC1", sequence="COL1"),
        PropertyValue(name="Yield", id="DAC2", sequence="COL2"),
    ]
    property_data = _property_data(columns)
    df = pd.DataFrame({"Viscosity": [1.0], "Yield": [2.0]})

    column_map = _get_column_map(dataframe=df, property_data=property_data)

    assert column_map["Viscosity"].id == "DAC1"
    assert column_map["Yield"].id == "DAC2"


def test_get_column_map_raises_when_column_not_found():
    """Test that a dataframe column with no matching data column raises ValueError."""
    columns = [PropertyValue(name="Viscosity", id="DAC1", sequence="COL1")]
    property_data = _property_data(columns)
    df = pd.DataFrame({"Unknown": [1.0]})

    with pytest.raises(ValueError, match="not found in block data columns"):
        _get_column_map(dataframe=df, property_data=property_data)


def test_get_column_map_raises_on_duplicate_column_name_matches():
    """Test that two data columns sharing a name raise ValueError for that column."""
    columns = [
        PropertyValue(name="Viscosity", id="DAC1", sequence="COL1"),
        PropertyValue(name="Viscosity", id="DAC2", sequence="COL2"),
    ]
    property_data = _property_data(columns)
    df = pd.DataFrame({"Viscosity": [1.0]})

    with pytest.raises(ValueError, match="multiple matches found"):
        _get_column_map(dataframe=df, property_data=property_data)


# ---------------------------------------------------------------------------
# _df_to_task_prop_create_list
# ---------------------------------------------------------------------------


def test_df_to_task_prop_create_list_builds_one_entry_per_cell():
    """Test that one TaskPropertyCreate is built per dataframe cell, row-major order."""
    column_map = {
        "Viscosity": PropertyValue(name="Viscosity", id="DAC1", sequence="COL1"),
        "Yield": PropertyValue(name="Yield", id="DAC2", sequence="COL2"),
    }
    df = pd.DataFrame({"Viscosity": [1.1, 2.2], "Yield": [10, 20]})

    result = _df_to_task_prop_create_list(
        dataframe=df, column_map=column_map, data_template_id="DAT1", interval="default"
    )

    assert len(result) == 4
    first = result[0]
    assert first.data_column.data_column_id == "DAC1"
    assert first.data_column.column_sequence == "COL1"
    assert first.value == "1.1"
    assert first.visible_trial_number == 1
    assert first.interval_combination == "default"
    assert first.data_template.id == "DAT1"

    last = result[-1]
    assert last.data_column.data_column_id == "DAC2"
    # iterrows() upcasts the whole row to a common dtype, so the mixed
    # int/float row renders the int column as a float-formatted string.
    assert last.value == "20.0"
    assert last.visible_trial_number == 2


def test_df_to_task_prop_create_list_raises_for_missing_column():
    """Test that a column_map entry missing from the dataframe raises ValueError."""
    df = pd.DataFrame({"Viscosity": [1.0]})
    column_map = {"Yield": PropertyValue(name="Yield", id="DAC2", sequence="COL2")}

    with pytest.raises(ValueError, match="not found in DataFrame"):
        _df_to_task_prop_create_list(
            dataframe=df, column_map=column_map, data_template_id="DAT1", interval="default"
        )


# ---------------------------------------------------------------------------
# trial_has_recorded_data
# ---------------------------------------------------------------------------


def test_trial_has_recorded_data_true_when_any_column_has_property_data():
    """Test that a trial with at least one populated column reports recorded data."""
    columns = [
        PropertyValue(name="A", sequence="COL1", property_data=None),
        PropertyValue(name="B", sequence="COL2", property_data=PropertyData(id="PTD1", value="5")),
    ]
    existing = _property_data(columns)

    assert (
        trial_has_recorded_data(
            existing_data_rows=existing, interval_combination="default", trial_number=1
        )
        is True
    )


def test_trial_has_recorded_data_false_when_no_column_has_property_data():
    """Test that a trial with no populated columns reports no recorded data."""
    columns = [PropertyValue(name="A", sequence="COL1", property_data=None)]
    existing = _property_data(columns)

    assert (
        trial_has_recorded_data(
            existing_data_rows=existing, interval_combination="default", trial_number=1
        )
        is False
    )


def test_trial_has_recorded_data_false_when_trial_not_found():
    """Test that a trial number with no matching row reports no recorded data."""
    columns = [
        PropertyValue(name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="5"))
    ]
    existing = _property_data(columns)

    assert (
        trial_has_recorded_data(
            existing_data_rows=existing, interval_combination="default", trial_number=99
        )
        is False
    )


# ---------------------------------------------------------------------------
# prepare_new_task_property
# ---------------------------------------------------------------------------


def test_prepare_new_task_property_returns_unchanged_when_trial_number_none():
    """Test that a None trial_number returns the property unchanged."""
    prop = _make_prop()
    existing = _property_data([PropertyValue(name="A", sequence="COL1", property_data=None)])

    result = prepare_new_task_property(prop=prop, existing_data_rows=existing, trial_number=None)

    assert result is prop


def test_prepare_new_task_property_keeps_trial_number_when_already_matching():
    """Test that a recorded trial keeps trial_number when it already equals the resolved one."""
    prop = _make_prop(trial_number=1)
    existing = _property_data(
        [
            PropertyValue(
                name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="1")
            )
        ]
    )

    result = prepare_new_task_property(prop=prop, existing_data_rows=existing, trial_number=1)

    assert result is prop
    assert result.trial_number == 1


def test_prepare_new_task_property_updates_trial_number_when_recorded_and_differs():
    """Test that a recorded trial gets trial_number rewritten when the caller's value differs."""
    prop = _make_prop(trial_number=5)
    existing = _property_data(
        [
            PropertyValue(
                name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="1")
            )
        ]
    )

    result = prepare_new_task_property(prop=prop, existing_data_rows=existing, trial_number=1)

    assert result is not prop
    assert result.trial_number == 1


def test_prepare_new_task_property_clears_trial_number_for_empty_placeholder_trial():
    """Test that an unrecorded placeholder trial clears an explicitly set trial_number."""
    prop = _make_prop(trial_number=7)
    existing = _property_data([PropertyValue(name="A", sequence="COL1", property_data=None)])

    result = prepare_new_task_property(prop=prop, existing_data_rows=existing, trial_number=1)

    assert result is not prop
    assert result.trial_number is None


def test_prepare_new_task_property_returns_unchanged_for_unset_trial_number_on_placeholder():
    """Test that an already-unset trial_number on a placeholder trial stays unchanged."""
    prop = _make_prop()
    existing = _property_data([PropertyValue(name="A", sequence="COL1", property_data=None)])

    result = prepare_new_task_property(prop=prop, existing_data_rows=existing, trial_number=1)

    assert result is prop


# ---------------------------------------------------------------------------
# resolve_trial_number
# ---------------------------------------------------------------------------


def test_resolve_trial_number_returns_explicit_value_without_lookup():
    """Test that an explicit trial_number short-circuits any visible-number lookup."""
    prop = _make_prop(trial_number=3)
    existing = _existing_with_visible_trials([(1, 1)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) == 3


def test_resolve_trial_number_returns_none_when_visible_trial_number_unset():
    """Test that no trial_number and no visible_trial_number resolves to None."""
    prop = TaskPropertyCreate.model_construct(
        data_column=TaskDataColumn(data_column_id="DAC1"),
        trial_number=None,
        visible_trial_number=None,
        interval_combination="default",
    )
    existing = _existing_with_visible_trials([(1, 1)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) is None


def test_resolve_trial_number_converts_string_visible_trial_number():
    """Test that a string visible_trial_number is converted to int before matching."""
    prop = TaskPropertyCreate.model_construct(
        data_column=TaskDataColumn(data_column_id="DAC1"),
        trial_number=None,
        visible_trial_number="2",
        interval_combination="default",
    )
    existing = _existing_with_visible_trials([(1, 1), (5, 2)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) == 5


def test_resolve_trial_number_returns_none_for_non_numeric_string():
    """Test that a non-numeric string visible_trial_number resolves to None."""
    prop = TaskPropertyCreate.model_construct(
        data_column=TaskDataColumn(data_column_id="DAC1"),
        trial_number=None,
        visible_trial_number="abc",
        interval_combination="default",
    )
    existing = _existing_with_visible_trials([(1, 1)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) is None


def test_resolve_trial_number_returns_none_when_no_visible_match():
    """Test that a visible_trial_number with no matching row resolves to None."""
    prop = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1"), value="1", visible_trial_number=99
    )
    existing = _existing_with_visible_trials([(1, 1)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) is None


def test_resolve_trial_number_returns_none_when_visible_match_is_ambiguous():
    """Test that more than one row sharing a visible_trial_number resolves to None."""
    prop = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1"), value="1", visible_trial_number=1
    )
    existing = _existing_with_visible_trials([(1, 1), (2, 1)])

    assert resolve_trial_number(prop=prop, existing_data_rows=existing) is None


# ---------------------------------------------------------------------------
# form_calculated_task_property_patches
# ---------------------------------------------------------------------------


def test_form_calculated_task_property_patches_recomputes_dependent_column():
    """Test that posting a source column recomputes its dependent calculated column."""
    existing = _existing_rows_with_calc(col_a_value="10", col_b_value="15")
    posted = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1", column_sequence="COL1"),
        value="10",
        trial_number=1,
    )

    patches = form_calculated_task_property_patches(
        existing_data_rows=existing, properties=[posted]
    )

    assert len(patches) == 1
    assert patches[0].property_column_id == "PTD2"
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].new_value == 20
    assert patches[0].old_value == "15"


def test_form_calculated_task_property_patches_skips_columns_not_used_in_any_calculation():
    """Test that posting a column no calculation depends on produces no patches."""
    existing = _existing_rows_with_calc()
    posted = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC2", column_sequence="COL2"),
        value="15",
        trial_number=1,
    )

    patches = form_calculated_task_property_patches(
        existing_data_rows=existing, properties=[posted]
    )

    assert patches == []


def test_form_calculated_task_property_patches_dedupes_same_interval_trial():
    """Test that two posted properties for the same interval/trial only recompute once."""
    existing = _existing_rows_with_calc()
    posted_a = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1", column_sequence="COL1"),
        value="10",
        trial_number=1,
    )
    posted_b = TaskPropertyCreate(
        data_column=TaskDataColumn(data_column_id="DAC1", column_sequence="COL1"),
        value="10",
        trial_number=1,
    )

    patches = form_calculated_task_property_patches(
        existing_data_rows=existing, properties=[posted_a, posted_b]
    )

    assert len(patches) == 1


def test_form_calculated_task_property_patches_skips_when_trial_number_unresolved():
    """Test that a property whose trial_number cannot be resolved is skipped."""
    existing = _existing_rows_with_calc()
    posted = TaskPropertyCreate.model_construct(
        data_column=TaskDataColumn(data_column_id="DAC1", column_sequence="COL1"),
        trial_number=None,
        visible_trial_number=999,
        interval_combination="default",
    )

    patches = form_calculated_task_property_patches(
        existing_data_rows=existing, properties=[posted]
    )

    assert patches == []


# ---------------------------------------------------------------------------
# get_on_platform_row
# ---------------------------------------------------------------------------


def test_get_on_platform_row_returns_matching_trial():
    """Test that a matching interval/trial number returns that trial row."""
    existing = _property_data([PropertyValue(name="A", sequence="COL1")])

    trial = get_on_platform_row(
        existing_data_rows=existing, interval_combination="default", trial_number=1
    )

    assert trial is not None
    assert trial.trial_number == 1


def test_get_on_platform_row_returns_none_when_no_match():
    """Test that no matching interval returns None."""
    existing = _property_data([PropertyValue(name="A", sequence="COL1")])

    assert (
        get_on_platform_row(
            existing_data_rows=existing, interval_combination="other", trial_number=1
        )
        is None
    )


# ---------------------------------------------------------------------------
# get_columns_used_in_calculation / get_all_columns_used_in_calculations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("calculation", "expected"),
    [
        (None, set()),
        ("=COL1+COL2", {"COL1", "COL2"}),
        ("=COL10*COL2", {"COL10", "COL2"}),
        ("no columns here", set()),
    ],
)
def test_get_columns_used_in_calculation(calculation, expected):
    """Test that COL# tokens are extracted from a calculation string."""
    assert get_columns_used_in_calculation(calculation=calculation, used_columns=set()) == expected


def test_get_all_columns_used_in_calculations_aggregates_across_columns():
    """Test that column tokens are aggregated across every calculation in the row."""
    columns = [
        SimpleNamespace(calculation="=COL1+COL2"),
        SimpleNamespace(calculation="=COL3/COL1"),
        SimpleNamespace(calculation=None),
    ]

    result = get_all_columns_used_in_calculations(first_row_data_column=columns)

    assert result == {"COL1", "COL2", "COL3"}


# ---------------------------------------------------------------------------
# _safe_eval_math (security boundary)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 + 2", 3),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("10 / 4", 2.5),
        ("10 % 3", 1),
        ("2 ** 3", 8),
        ("-5", -5),
        ("+5", 5),
        ("log10(100)", 2.0),
        ("ln(1)", 0.0),
        ("sqrt(9)", 3.0),
        ("pi", math.pi),
        ("pi()", math.pi),
        ("(2 + 3) * 4", 20),
    ],
)
def test_safe_eval_math_evaluates_arithmetic(expression, expected):
    """Test that supported arithmetic and allow-listed functions evaluate correctly."""
    assert _safe_eval_math(expression=expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "os.system('echo hi')",
        "().__class__",
        "(1).__class__.__bases__",
        "[].__class__",
        "open('/etc/passwd')",
        "some_name",
        "abs(-5)",
        "log10(1, 2)",
        "log10(x=1)",
        "1; 2",
        "print('x')",
        "'a string'",
        "[1, 2, 3]",
    ],
)
def test_safe_eval_math_rejects_unsafe_expressions(expression):
    """Test that names, attribute access, calls, imports, and non-allow-listed functions are rejected."""
    with pytest.raises((ValueError, SyntaxError)):
        _safe_eval_math(expression=expression)


# ---------------------------------------------------------------------------
# evaluate_calculation
# ---------------------------------------------------------------------------


def test_evaluate_calculation_substitutes_columns_and_computes():
    """Test that column tokens are substituted with their values before evaluation."""
    assert (
        evaluate_calculation(calculation="=COL1+COL2", column_values={"COL1": "10", "COL2": "5"})
        == 15
    )


def test_evaluate_calculation_supports_caret_as_power():
    """Test that '^' is treated as exponentiation."""
    assert evaluate_calculation(calculation="COL1^2", column_values={"COL1": "3"}) == 9


def test_evaluate_calculation_returns_none_when_a_column_is_unresolved():
    """Test that a referenced column missing from column_values returns None instead of raising."""
    assert evaluate_calculation(calculation="=COL1+COL2", column_values={"COL1": "10"}) is None


def test_evaluate_calculation_returns_none_on_invalid_expression():
    """Test that a syntactically invalid expression returns None instead of raising."""
    assert evaluate_calculation(calculation="=1/", column_values={}) is None


# ---------------------------------------------------------------------------
# generate_data_patch_payload
# ---------------------------------------------------------------------------


def test_generate_data_patch_payload_adds_when_stored_value_is_none():
    """Test that a calculated column with no stored value emits an ADD patch."""
    col_a = PropertyValue(
        name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="10")
    )
    col_b = PropertyValue(
        name="B",
        sequence="COL2",
        calculation="=COL1*2",
        property_data=PropertyData(id="PTD2", value=None),
    )
    trial = Trial(trial_number=1, data_columns=[col_a, col_b])

    patches = generate_data_patch_payload(trial=trial)

    assert len(patches) == 1
    assert patches[0].operation == PatchOperation.ADD
    assert patches[0].property_column_id == "PTD2"
    assert patches[0].new_value == 20
    assert patches[0].old_value is None


def test_generate_data_patch_payload_updates_when_stored_value_changed():
    """Test that a calculated column whose recomputed value differs emits an UPDATE patch."""
    col_a = PropertyValue(
        name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="10")
    )
    col_b = PropertyValue(
        name="B",
        sequence="COL2",
        calculation="=COL1*2",
        property_data=PropertyData(id="PTD2", value="99"),
    )
    trial = Trial(trial_number=1, data_columns=[col_a, col_b])

    patches = generate_data_patch_payload(trial=trial)

    assert len(patches) == 1
    assert patches[0].operation == PatchOperation.UPDATE
    assert patches[0].new_value == 20
    assert patches[0].old_value == "99"


def test_generate_data_patch_payload_no_op_when_value_unchanged():
    """Test that a calculated column whose recomputed value matches emits no patch."""
    col_a = PropertyValue(
        name="A", sequence="COL1", property_data=PropertyData(id="PTD1", value="10")
    )
    col_b = PropertyValue(
        name="B",
        sequence="COL2",
        calculation="=COL1*2",
        property_data=PropertyData(id="PTD2", value="20"),
    )
    trial = Trial(trial_number=1, data_columns=[col_a, col_b])

    assert generate_data_patch_payload(trial=trial) == []


def test_generate_data_patch_payload_skips_non_calculated_or_unpopulated_columns():
    """Test that columns with no calculation, or a calculation but no stored value, are skipped."""
    col_a = PropertyValue(name="A", sequence="COL1", property_data=None)
    col_b = PropertyValue(name="B", sequence="COL2", calculation="=COL1*2", property_data=None)
    trial = Trial(trial_number=1, data_columns=[col_a, col_b])

    assert generate_data_patch_payload(trial=trial) == []


# ---------------------------------------------------------------------------
# _setpoint_display_value
# ---------------------------------------------------------------------------


def test_setpoint_display_value_none_returns_none():
    """Test that None input returns None."""
    assert _setpoint_display_value(None) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [("abc", "abc"), (5, "5"), (5.5, "5.5"), (True, "True")],
)
def test_setpoint_display_value_scalars_are_stringified(value, expected):
    """Test that scalar values (str, int, float, bool) are stringified as-is."""
    assert _setpoint_display_value(value) == expected


def test_setpoint_display_value_dict_prefers_name_over_id():
    """Test that a dict value prefers its 'name' key over 'id'."""
    assert _setpoint_display_value({"name": "Oven", "id": "INV1"}) == "Oven"


def test_setpoint_display_value_dict_falls_back_to_id():
    """Test that a dict value without 'name' falls back to 'id'."""
    assert _setpoint_display_value({"id": "INV1"}) == "INV1"


def test_setpoint_display_value_dict_falls_back_to_str_repr():
    """Test that a dict with neither 'name' nor 'id' falls back to its string form."""
    value = {"other": "x"}
    assert _setpoint_display_value(value) == str(value)


def test_setpoint_display_value_object_prefers_name_attribute():
    """Test that an object value prefers its 'name' attribute over 'id'."""
    obj = SimpleNamespace(name="Oven", id="INV1")
    assert _setpoint_display_value(obj) == "Oven"


def test_setpoint_display_value_object_falls_back_to_id_attribute():
    """Test that an object value without a 'name' attribute falls back to 'id'."""
    obj = SimpleNamespace(id="INV1")
    assert _setpoint_display_value(obj) == "INV1"


def test_setpoint_display_value_object_falls_back_to_str():
    """Test that an object with neither attribute falls back to its string form."""

    class Custom:
        def __str__(self):
            return "custom-repr"

    assert _setpoint_display_value(Custom()) == "custom-repr"


# ---------------------------------------------------------------------------
# build_interval_setpoint_map
# ---------------------------------------------------------------------------


def test_build_interval_setpoint_map_empty_workflow_has_default_only():
    """Test that a workflow with no setpoints yields only an empty 'default' entry."""
    workflow = Workflow(id="WFL1")

    assert build_interval_setpoint_map(workflow=workflow) == {"default": {}}


def test_build_interval_setpoint_map_fixed_setpoints_populate_default():
    """Test that non-intervalized setpoints populate the 'default' entry."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM1", name="Temp", value="25")
                ],
            )
        ],
    )

    assert build_interval_setpoint_map(workflow=workflow) == {"default": {"Temp": "25"}}


def test_build_interval_setpoint_map_single_intervalized_parameter():
    """Test that each interval of a single intervalized parameter gets its own setpoint entry."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        name="Temp",
                        intervals=[
                            Interval(value="25", row_id="ROW1"),
                            Interval(value="60", row_id="ROW2"),
                        ],
                    )
                ],
            )
        ],
        interval_combinations=[
            IntervalCombination(interval_id="ROW1"),
            IntervalCombination(interval_id="ROW2"),
        ],
    )

    result = build_interval_setpoint_map(workflow=workflow)

    assert result["ROW1"] == {"Temp": "25"}
    assert result["ROW2"] == {"Temp": "60"}
    assert result["default"] == {}


def test_build_interval_setpoint_map_cartesian_combination_includes_fixed_setpoints():
    """Test that a cartesian interval combines varied parameters with fixed ones."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM1", name="Pressure", value="1atm"),
                    ParameterSetpoint(
                        parameter_id="PRM2",
                        name="Temp",
                        intervals=[
                            Interval(value="25", row_id="ROW1"),
                            Interval(value="60", row_id="ROW2"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM3",
                        name="Speed",
                        intervals=[
                            Interval(value="100", row_id="ROW3"),
                            Interval(value="200", row_id="ROW4"),
                        ],
                    ),
                ],
            )
        ],
        interval_combinations=[IntervalCombination(interval_id="ROW1XROW3")],
    )

    result = build_interval_setpoint_map(workflow=workflow)

    assert result["ROW1XROW3"] == {"Pressure": "1atm", "Temp": "25", "Speed": "100"}


def test_build_interval_setpoint_map_skips_unresolvable_interval_id():
    """Test that an interval id referencing an unknown row is left out of the map."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        name="Temp",
                        intervals=[Interval(value="25", row_id="ROW1")],
                    )
                ],
            )
        ],
        interval_combinations=[IntervalCombination(interval_id="ROW1XROW99")],
    )

    result = build_interval_setpoint_map(workflow=workflow)

    assert "ROW1XROW99" not in result


def test_build_interval_setpoint_map_skips_interval_with_no_row_id():
    """Test that an interval value with no row_id is not added to the varied map."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        name="Temp",
                        intervals=[Interval(value="25", row_id=None)],
                    )
                ],
            )
        ],
    )

    result = build_interval_setpoint_map(workflow=workflow)

    assert result == {"default": {}}


def test_build_interval_setpoint_map_skips_fixed_setpoint_with_no_display_value():
    """Test that a fixed setpoint whose value has no display form is left out of 'default'."""
    workflow = Workflow(
        id="WFL1",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM1", name="Temp", value=None)
                ],
            )
        ],
    )

    result = build_interval_setpoint_map(workflow=workflow)

    assert result == {"default": {}}


# ---------------------------------------------------------------------------
# map_block_final_workflows
# ---------------------------------------------------------------------------


def test_map_block_final_workflows_prefers_final_category():
    """Test that the FINAL-category workflow is chosen when multiple are present."""
    initial = Workflow(id="WFL1", category="INITIAL")
    final = Workflow(id="WFL2", category="FINAL")
    block = Block(id="BLK1", workflow=[initial, final], data_template=[{"id": "DAT1"}])
    task = PropertyTask(name="T", blocks=[block])

    result = map_block_final_workflows(task=task)

    assert result == {"BLK1": final}


def test_map_block_final_workflows_falls_back_to_first_when_no_final():
    """Test that the first workflow is used when none is category FINAL."""
    initial = Workflow(id="WFL1", category="INITIAL")
    block = Block(id="BLK1", workflow=[initial], data_template=[{"id": "DAT1"}])
    task = PropertyTask(name="T", blocks=[block])

    result = map_block_final_workflows(task=task)

    assert result == {"BLK1": initial}


def test_map_block_final_workflows_empty_for_task_with_no_blocks():
    """Test that a task with no blocks maps to an empty dict."""
    task = PropertyTask(name="T", blocks=None)

    assert map_block_final_workflows(task=task) == {}


# ---------------------------------------------------------------------------
# flatten_task_property_data
# ---------------------------------------------------------------------------


def test_flatten_task_property_data_produces_one_record_per_column():
    """Test that each trial's data column becomes one flattened record."""
    prop_data = PropertyData(id="PTD1", value="99")
    col_with_value = PropertyValue(
        name="Viscosity",
        id="DAC1",
        sequence="COL1",
        property_data=prop_data,
        unit={"id": "UNI1", "name": "cP"},
        value="5.5",
        numeric_value=5.5,
    )
    # column.value is None -> falls back to property_data.value
    col_falls_back = PropertyValue(
        name="Yield",
        id="DAC2",
        sequence="COL2",
        property_data=prop_data,
        value=None,
        numeric_value=None,
    )
    trial = Trial(
        trial_number=1,
        visible_trial_number=1,
        void=False,
        data_columns=[col_with_value, col_falls_back],
    )
    interval = DataInterval(
        interval_combination="ROW1", trials=[trial], name="Fallback Name", void=True
    )
    block = TaskPropertyData(
        parent_id="TAS1",
        block_id="BLK1",
        data=[interval],
        inventory=PropertyDataInventoryInformation(inventory_id="INV1", lot_id="LOT1"),
        data_template={"id": "DAT1", "name": "DT Name"},
    )

    records = flatten_task_property_data(
        block=block,
        task_id="TAS1",
        workflow_id="WFL1",
        workflow_name="WF Name",
        interval_setpoints={"ROW1": {"Temp": "25"}},
        interval_descriptions={"ROW1": "Temp: 25"},
    )

    assert len(records) == 2
    first, second = records
    assert first.task_id == "TAS1"
    assert first.block_id == "BLK1"
    assert first.data_template_id == "DAT1"
    assert first.data_template_name == "DT Name"
    assert first.inventory_id == "INV1"
    assert first.lot_id == "LOT1"
    assert first.interval_combination == "ROW1"
    assert first.interval_description == "Temp: 25"
    assert first.parameter_setpoints == {"Temp": "25"}
    assert first.void is True
    assert first.value == "5.5"
    assert first.unit_name == "cP"
    assert first.workflow_id == "WFL1"
    assert first.workflow_name == "WF Name"

    # falls back to property_data.value when column.value is None
    assert second.value == "99"


def test_flatten_task_property_data_falls_back_to_interval_name_for_description():
    """Test that the interval's own name is used when no description mapping matches."""
    col = PropertyValue(name="Viscosity", id="DAC1", sequence="COL1", value="1")
    trial = Trial(trial_number=1, data_columns=[col])
    interval = DataInterval(interval_combination="ROW9", trials=[trial], name="  Raw Name  ")
    block = TaskPropertyData(parent_id="TAS1", block_id="BLK1", data=[interval])

    records = flatten_task_property_data(
        block=block,
        task_id="TAS1",
        workflow_id=None,
        workflow_name=None,
        interval_setpoints={},
        interval_descriptions={},
    )

    assert records[0].interval_description == "Raw Name"


def test_flatten_task_property_data_reads_dict_shaped_unit():
    """Test that a raw dict unit (not coerced to a Unit model) still resolves unit_name."""
    col = PropertyValue.model_construct(
        name="Viscosity",
        id="DAC1",
        sequence="COL1",
        value="1",
        numeric_value=None,
        calculation=None,
        property_data=None,
        unit={"name": "grams"},
        hidden=False,
        data_column_unique_id=None,
    )
    trial = Trial(trial_number=1, data_columns=[col])
    interval = DataInterval(interval_combination="default", trials=[trial])
    block = TaskPropertyData(parent_id="TAS1", block_id="BLK1", data=[interval])

    records = flatten_task_property_data(
        block=block,
        task_id="TAS1",
        workflow_id=None,
        workflow_name=None,
        interval_setpoints={},
        interval_descriptions={},
    )

    assert records[0].unit_name == "grams"
