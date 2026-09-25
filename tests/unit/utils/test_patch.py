"""Unit tests for the generic PATCH payload builders in ``albert.utils._patch``.

Allowed under the patch-builder exception in OPINIONS.md: these guard non-obvious
diff behavior with no I/O to fake.
"""

import pytest

from albert.core.shared.models.patch import (
    DTPatchDatum,
    GeneralPatchDatum,
    GeneralPatchPayload,
    PatchPayload,
    PGPatchDatum,
)
from albert.resources.data_templates import CurveDataEntityLink, DataColumnValue, DataTemplate
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    ParameterGroup,
    ParameterValue,
    PGType,
    ValueValidation,
)
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.users import User
from albert.utils._patch import (
    _data_column_calculation_patches,
    _data_column_unit_patches,
    _data_column_value_patches,
    _normalize_curve_links,
    _parameter_required_patch,
    _parameter_unit_patches,
    _parameter_value_patches,
    build_acl_patch_payload,
    data_column_curve_data_patches,
    data_column_validation_patches,
    generate_data_column_patches,
    generate_data_template_patches,
    generate_enum_patches,
    generate_parameter_group_patches,
    generate_parameter_patches,
    handle_tags,
    parameter_validation_patch,
)


def _pv(**kwargs) -> ParameterValue:
    kwargs.setdefault("id", "PRM1")
    kwargs.setdefault("sequence", "1")
    return ParameterValue(**kwargs)


def _dc(**kwargs) -> DataColumnValue:
    kwargs.setdefault("data_column_id", "DAC1")
    kwargs.setdefault("sequence", "1")
    return DataColumnValue(**kwargs)


# ---------------------------------------------------------------------------
# _parameter_unit_patches / _data_column_unit_patches
# ---------------------------------------------------------------------------


def test_parameter_unit_patches_unchanged_is_no_op():
    """Test that identical units emit no patch."""
    assert _parameter_unit_patches(_pv(unit=None), _pv(unit=None)) is None
    unit = Unit(id="UNI1", name="mL")
    assert _parameter_unit_patches(_pv(unit=unit), _pv(unit=unit)) is None


def test_parameter_unit_patches_newly_set_emits_add():
    """Test that a unit set from None emits an ADD op keyed to the row sequence."""
    patch = _parameter_unit_patches(_pv(unit=None), _pv(unit=Unit(id="UNI1", name="mL")))

    assert patch == PGPatchDatum(operation="add", attribute="unitId", newValue="UNI1", rowId="1")


def test_parameter_unit_patches_cleared_emits_delete():
    """Test that a unit cleared to None emits a DELETE op with the old unit id."""
    patch = _parameter_unit_patches(_pv(unit=Unit(id="UNI1", name="mL")), _pv(unit=None))

    assert patch == PGPatchDatum(
        operation="delete", attribute="unitId", oldValue="UNI1", rowId="1"
    )


def test_parameter_unit_patches_changed_emits_update():
    """Test that a changed unit id emits an UPDATE op with old and new values."""
    patch = _parameter_unit_patches(
        _pv(unit=Unit(id="UNI1", name="mL")), _pv(unit=Unit(id="UNI2", name="L"))
    )

    assert patch == PGPatchDatum(
        operation="update", attribute="unitId", oldValue="UNI1", newValue="UNI2", rowId="1"
    )


def test_data_column_unit_patches_mirrors_parameter_behavior():
    """Test that a data column unit change emits an UPDATE keyed to colId (not rowId)."""
    patch = _data_column_unit_patches(
        _dc(unit=Unit(id="UNI1", name="mL")), _dc(unit=Unit(id="UNI2", name="L"))
    )

    assert patch == DTPatchDatum(
        operation="update", attribute="unit", oldValue="UNI1", newValue="UNI2", colId="1"
    )


def test_data_column_unit_patches_unchanged_is_no_op():
    """Test that identical data column units emit no patch."""
    unit = Unit(id="UNI1", name="mL")
    assert _data_column_unit_patches(_dc(unit=unit), _dc(unit=unit)) is None


def test_data_column_unit_patches_newly_set_emits_add():
    """Test that a data column unit set from None emits an ADD op."""
    patch = _data_column_unit_patches(_dc(unit=None), _dc(unit=Unit(id="UNI1", name="mL")))

    assert patch == DTPatchDatum(operation="add", attribute="unit", newValue="UNI1", colId="1")


def test_data_column_unit_patches_cleared_emits_delete():
    """Test that a data column unit cleared to None emits a DELETE op."""
    patch = _data_column_unit_patches(_dc(unit=Unit(id="UNI1", name="mL")), _dc(unit=None))

    assert patch == DTPatchDatum(operation="delete", attribute="unit", oldValue="UNI1", colId="1")


@pytest.mark.parametrize(
    "builder,patch_fn",
    [
        pytest.param(_pv, _parameter_unit_patches, id="parameter"),
        pytest.param(_dc, _data_column_unit_patches, id="data-column"),
    ],
)
def test_unit_patches_same_id_different_metadata_is_no_op(builder, patch_fn):
    """Test that units with the same id but different other fields are still unchanged.

    Only the unit id is compared once both sides are non-None; a metadata-only
    difference (e.g. a corrected display name) must not trigger a spurious op.
    """
    initial = builder(unit=Unit(id="UNI1", name="milliliter", symbol="mL"))
    updated = builder(unit=Unit(id="UNI1", name="millilitre", symbol="ml"))

    assert patch_fn(initial, updated) is None


# ---------------------------------------------------------------------------
# _parameter_value_patches / _data_column_value_patches
# ---------------------------------------------------------------------------


def test_parameter_value_patches_matrix():
    """Test the add/update/delete/no-op matrix for a parameter's value."""
    assert _parameter_value_patches(_pv(value=None), _pv(value=None)) is None
    assert _parameter_value_patches(_pv(value="500"), _pv(value="500")) is None

    add = _parameter_value_patches(_pv(value=None), _pv(value="500"))
    assert add == PGPatchDatum(operation="add", attribute="value", newValue="500", rowId="1")

    delete = _parameter_value_patches(_pv(value="500"), _pv(value=None))
    assert delete == PGPatchDatum(operation="delete", attribute="value", oldValue="500", rowId="1")

    update = _parameter_value_patches(_pv(value="500"), _pv(value="600"))
    assert update == PGPatchDatum(
        operation="update", attribute="value", oldValue="500", newValue="600", rowId="1"
    )


def test_data_column_value_patches_matrix():
    """Test the add/update/delete/no-op matrix for a data column's value."""
    assert _data_column_value_patches(_dc(value=None), _dc(value=None)) is None
    assert _data_column_value_patches(_dc(value="10"), _dc(value="10")) is None

    add = _data_column_value_patches(_dc(value=None), _dc(value="10"))
    assert add == DTPatchDatum(operation="add", attribute="value", newValue="10", colId="1")

    delete = _data_column_value_patches(_dc(value="10"), _dc(value=None))
    assert delete == DTPatchDatum(operation="delete", attribute="value", oldValue="10", colId="1")

    update = _data_column_value_patches(_dc(value="10"), _dc(value="11"))
    assert update == DTPatchDatum(
        operation="update", attribute="value", oldValue="10", newValue="11", colId="1"
    )


# ---------------------------------------------------------------------------
# _data_column_calculation_patches
# ---------------------------------------------------------------------------


def test_data_column_calculation_patches_matrix():
    """Test the add/update/delete/no-op matrix for a data column's calculation."""
    assert _data_column_calculation_patches(_dc(calculation=None), _dc(calculation=None)) is None
    assert _data_column_calculation_patches(_dc(calculation="A+B"), _dc(calculation="A+B")) is None

    add = _data_column_calculation_patches(_dc(calculation=None), _dc(calculation="A+B"))
    assert add == DTPatchDatum(operation="add", attribute="calculation", newValue="A+B", colId="1")

    delete = _data_column_calculation_patches(_dc(calculation="A+B"), _dc(calculation=None))
    assert delete == DTPatchDatum(
        operation="delete", attribute="calculation", oldValue="A+B", colId="1"
    )

    update = _data_column_calculation_patches(_dc(calculation="A+B"), _dc(calculation="A-B"))
    assert update == DTPatchDatum(
        operation="update", attribute="calculation", oldValue="A+B", newValue="A-B", colId="1"
    )


# ---------------------------------------------------------------------------
# data_column_validation_patches
# ---------------------------------------------------------------------------


def test_data_column_validation_patches_unchanged_is_no_op():
    """Test that identical validation lists emit no patch, including both-empty."""
    assert data_column_validation_patches(_dc(validation=[]), _dc(validation=[])) is None
    same = [ValueValidation(datatype=DataType.NUMBER, min="0")]
    assert data_column_validation_patches(_dc(validation=same), _dc(validation=list(same))) is None


def test_data_column_validation_patches_none_to_list_emits_add():
    """Test that validation set from an explicit None emits an ADD with the full list."""
    validation = [ValueValidation(datatype=DataType.NUMBER)]
    initial = DataColumnValue.model_construct(data_column_id="DAC1", sequence="1", validation=None)
    patch = data_column_validation_patches(initial, _dc(validation=validation))

    assert patch.operation == "add"
    assert patch.attribute == "validation"
    assert patch.new_value == validation


def test_data_column_validation_patches_list_to_none_emits_delete():
    """Test that validation cleared to an explicit None emits a DELETE with the old list."""
    validation = [ValueValidation(datatype=DataType.NUMBER)]
    updated = DataColumnValue.model_construct(data_column_id="DAC1", sequence="1", validation=None)
    patch = data_column_validation_patches(_dc(validation=validation), updated)

    assert patch.operation == "delete"
    assert patch.old_value == validation


def test_data_column_validation_patches_datatype_change_emits_update_with_old_value():
    """Test that a non-enum validation change emits an UPDATE carrying old and new values."""
    initial = [ValueValidation(datatype=DataType.NUMBER, min="0")]
    updated = [ValueValidation(datatype=DataType.STRING)]

    patch = data_column_validation_patches(_dc(validation=initial), _dc(validation=updated))

    assert patch.operation == "update"
    assert patch.old_value == initial
    assert patch.new_value == updated


def test_data_column_validation_patches_enum_value_only_change_is_no_op():
    """Test that an ENUM validation's option values changing alone emits no patch.

    Enum option changes are surfaced separately via ``generate_enum_patches``; the
    general validation diff must ignore them so both mechanisms don't double-patch.
    """
    initial = [
        ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(id="E1", text="Low")])
    ]
    updated = [
        ValueValidation(
            datatype=DataType.ENUM,
            value=[EnumValidationValue(id="E1", text="Low"), EnumValidationValue(text="High")],
        )
    ]

    assert data_column_validation_patches(_dc(validation=initial), _dc(validation=updated)) is None


# ---------------------------------------------------------------------------
# _normalize_curve_links / data_column_curve_data_patches
# ---------------------------------------------------------------------------


def test_normalize_curve_links_none_returns_empty_list():
    """Test that None curve links normalize to an empty list."""
    assert _normalize_curve_links(None) == []


def test_normalize_curve_links_sorts_by_id_and_axis():
    """Test that curve links are sorted for order-independent comparison."""
    links = [
        CurveDataEntityLink(id="DACB", axis="Y"),
        CurveDataEntityLink(id="DACA", axis="X"),
    ]
    assert [x.id for x in _normalize_curve_links(links)] == ["DACA", "DACB"]


def test_data_column_curve_data_patches_reordered_only_is_no_op():
    """Test that curve links in a different order are treated as unchanged."""
    a = CurveDataEntityLink(id="A", axis="X")
    b = CurveDataEntityLink(id="B", axis="Y")
    initial = _dc(curve_data=[a, b])
    updated = _dc(curve_data=[b, a])

    assert data_column_curve_data_patches(initial, updated) is None


def test_data_column_curve_data_patches_add_and_delete():
    """Test that curve data set from/to None emits ADD/DELETE with the full link list."""
    link = CurveDataEntityLink(id="A", axis="X")

    add = data_column_curve_data_patches(_dc(curve_data=None), _dc(curve_data=[link]))
    assert add.operation == "add"
    assert add.new_value == [link]

    delete = data_column_curve_data_patches(_dc(curve_data=[link]), _dc(curve_data=None))
    assert delete.operation == "delete"
    assert delete.old_value == [link]


def test_data_column_curve_data_patches_changed_emits_update():
    """Test that a changed curve link set emits an UPDATE with old and new lists."""
    initial = [CurveDataEntityLink(id="A", axis="X")]
    updated = [CurveDataEntityLink(id="B", axis="X")]

    patch = data_column_curve_data_patches(_dc(curve_data=initial), _dc(curve_data=updated))

    assert patch.operation == "update"
    assert patch.old_value == initial
    assert patch.new_value == updated


# ---------------------------------------------------------------------------
# _parameter_required_patch
# ---------------------------------------------------------------------------


def test_parameter_required_patch_none_on_updated_is_always_no_op():
    """Test that ``required`` left None on updated is a no-op, even if initial was set."""
    assert _parameter_required_patch(_pv(required=None), _pv(required=None)) is None
    assert _parameter_required_patch(_pv(required=True), _pv(required=None)) is None


def test_parameter_required_patch_unset_initial_emits_add():
    """Test that ``required`` newly set (initial unset) emits an ADD, not an UPDATE.

    An UPDATE is rejected by the backend when there is no existing value to match.
    """
    patch = _parameter_required_patch(_pv(required=None), _pv(required=True))

    assert patch == PGPatchDatum(operation="add", attribute="required", newValue=True, rowId="1")


def test_parameter_required_patch_changed_emits_update():
    """Test that a changed ``required`` flag emits an UPDATE with the old value."""
    patch = _parameter_required_patch(_pv(required=False), _pv(required=True))

    assert patch == PGPatchDatum(
        operation="update", attribute="required", oldValue=False, newValue=True, rowId="1"
    )


def test_parameter_required_patch_unchanged_is_no_op():
    """Test that an unchanged ``required`` flag emits no patch."""
    assert _parameter_required_patch(_pv(required=True), _pv(required=True)) is None


# ---------------------------------------------------------------------------
# parameter_validation_patch
# ---------------------------------------------------------------------------


def test_parameter_validation_patch_both_empty_is_no_op():
    """Test that two default (empty) validation lists emit no patch."""
    assert parameter_validation_patch(_pv(), _pv()) is None


def test_parameter_validation_patch_same_datatype_unchanged_is_no_op():
    """Test that an unchanged, non-enum validation list emits no patch."""
    validation = [ValueValidation(datatype=DataType.NUMBER, min="0")]
    assert (
        parameter_validation_patch(_pv(validation=validation), _pv(validation=list(validation)))
        is None
    )


def test_parameter_validation_patch_enum_value_only_change_is_no_op():
    """Test that ENUM option values changing alone emits no patch (handled by enum_patches)."""
    initial = [
        ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(id="E1", text="Low")])
    ]
    updated = [
        ValueValidation(
            datatype=DataType.ENUM,
            value=[EnumValidationValue(id="E1", text="Low"), EnumValidationValue(text="High")],
        )
    ]

    assert parameter_validation_patch(_pv(validation=initial), _pv(validation=updated)) is None


def test_parameter_validation_patch_none_to_list_emits_add():
    """Test that validation set from an explicit None emits an ADD with the full list."""
    validation = [ValueValidation(datatype=DataType.NUMBER)]
    initial = ParameterValue.model_construct(
        id="PRM1", sequence="1", validation=None, parameter=None
    )

    patch = parameter_validation_patch(initial, _pv(validation=validation))

    assert patch.operation == "add"
    assert patch.new_value == validation


def test_parameter_validation_patch_list_to_none_emits_delete():
    """Test that validation cleared to an explicit None emits a DELETE with the old list."""
    validation = [ValueValidation(datatype=DataType.NUMBER)]
    updated = ParameterValue.model_construct(
        id="PRM1", sequence="1", validation=None, parameter=None
    )

    patch = parameter_validation_patch(_pv(validation=validation), updated)

    assert patch.operation == "delete"
    assert patch.old_value == validation


def test_parameter_validation_patch_cleared_to_empty_list_emits_update_not_no_op():
    """Test that clearing validation to [] (not None) is a real update, never a no-op."""
    validation = [ValueValidation(datatype=DataType.NUMBER)]

    patch = parameter_validation_patch(_pv(validation=validation), _pv(validation=[]))

    assert patch.operation == "update"
    assert patch.new_value == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: parameter_validation_patch's update branch "
        "(src/albert/utils/_patch.py:353-359) never sets old_value, unlike the "
        "equivalent data_column_validation_patches update branch."
    ),
)
def test_parameter_validation_patch_update_op_carries_old_value():
    """Test that a non-enum validation change emits an UPDATE carrying the old value."""
    initial = [ValueValidation(datatype=DataType.NUMBER)]
    updated = [ValueValidation(datatype=DataType.STRING)]

    patch = parameter_validation_patch(_pv(validation=initial), _pv(validation=updated))

    assert patch.operation == "update"
    assert patch.old_value == initial


# ---------------------------------------------------------------------------
# generate_enum_patches
# ---------------------------------------------------------------------------


def test_generate_enum_patches_no_change_returns_empty_list():
    """Test that identical enum lists (including both None) emit no patches."""
    assert generate_enum_patches(None, None) == []
    same = [EnumValidationValue(id="E1", text="Low")]
    assert generate_enum_patches(same, list(same)) == []


def test_generate_enum_patches_add_new_option():
    """Test that a new enum option (no id) emits an add patch."""
    existing = [EnumValidationValue(id="E1", text="Low")]
    updated = [EnumValidationValue(id="E1", text="Low"), EnumValidationValue(text="High")]

    assert generate_enum_patches(existing, updated) == [{"operation": "add", "text": "High"}]


def test_generate_enum_patches_delete_removed_option():
    """Test that an existing option missing from updated emits a delete patch."""
    existing = [EnumValidationValue(id="E1", text="Low"), EnumValidationValue(id="E2", text="Hi")]
    updated = [EnumValidationValue(id="E1", text="Low")]

    assert generate_enum_patches(existing, updated) == [{"operation": "delete", "id": "E2"}]


def test_generate_enum_patches_rename_existing_option():
    """Test that an existing option with a changed text emits an update patch."""
    existing = [EnumValidationValue(id="E1", text="Low")]
    updated = [EnumValidationValue(id="E1", text="Lowest")]

    assert generate_enum_patches(existing, updated) == [
        {"operation": "update", "id": "E1", "text": "Lowest"}
    ]


def test_generate_enum_patches_new_option_matching_existing_text_is_rehydrated():
    """Test that a new (id-less) option matching an existing option's text is a no-op.

    This lets a caller re-add an option by name without knowing its id; it is
    matched back onto the existing entry rather than treated as a new one.
    """
    existing = [EnumValidationValue(id="E1", text="Low")]
    updated = [EnumValidationValue(text="Low")]

    assert generate_enum_patches(existing, updated) == []


def test_generate_enum_patches_ignores_non_enum_validation_value_entries():
    """Test that non-EnumValidationValue entries in either list are filtered out."""
    existing = [EnumValidationValue(id="E1", text="Low"), "not-an-enum-value"]
    updated = [EnumValidationValue(id="E1", text="Low")]

    assert generate_enum_patches(existing, updated) == []


# ---------------------------------------------------------------------------
# generate_data_column_patches
# ---------------------------------------------------------------------------


def test_generate_data_column_patches_none_inputs_return_empty():
    """Test that None initial/updated data columns produce empty results."""
    patches, new_cols, enum_patches = generate_data_column_patches(None, None)

    assert patches == []
    assert new_cols == []
    assert enum_patches == {}


def test_generate_data_column_patches_new_column_is_not_patched():
    """Test that a column with no matching sequence is classified as new, not patched."""
    patches, new_cols, _ = generate_data_column_patches(
        initial_data_column=[],
        updated_data_column=[_dc(data_column_id="DAC1", sequence=None, value="30")],
    )

    assert patches == []
    assert len(new_cols) == 1
    assert new_cols[0].value == "30"


def test_generate_data_column_patches_deleted_columns_emit_one_op_each():
    """Test that each deleted column emits its own single-sequence delete op.

    The backend only accepts one "datacolumns" delete op per sequence per
    request, so deletions must never be batched into a single oldValue list.
    """
    initial = [_dc(sequence="1"), _dc(sequence="2")]

    patches, _, _ = generate_data_column_patches(initial, [])

    delete_ops = [p for p in patches if p.attribute == "datacolumns"]
    assert len(delete_ops) == 2
    assert {tuple(op.old_value) for op in delete_ops} == {("1",), ("2",)}


def test_generate_data_column_patches_unchanged_column_emits_nothing():
    """Test that a column matched by sequence with no field changes emits no patch."""
    col = _dc(sequence="1", value="10")

    patches, new_cols, enum_patches = generate_data_column_patches(
        [col], [_dc(sequence="1", value="10")]
    )

    assert patches == []
    assert new_cols == []
    assert enum_patches == {}


def test_generate_data_column_patches_field_changes_wrap_in_general_patch_datum():
    """Test that value/calculation/validation/curve changes are grouped under one action list."""
    initial = [_dc(sequence="1", value="10", calculation=None)]
    updated = [_dc(sequence="1", value="11", calculation="A+B")]

    patches, _, _ = generate_data_column_patches(initial, updated)

    assert len(patches) == 1
    grouped = patches[0]
    assert isinstance(grouped, GeneralPatchDatum)
    assert grouped.attribute == "datacolumn"
    assert grouped.colId == "1"
    action_attrs = {a.attribute for a in grouped.actions}
    assert action_attrs == {"value", "calculation"}
    # colId is stripped from individual actions; it lives only on the wrapper.
    assert all(a.colId is None for a in grouped.actions)


def test_generate_data_column_patches_unit_change_is_a_separate_top_level_patch():
    """Test that a unit-only change is emitted as its own top-level patch, not grouped."""
    initial = [_dc(sequence="1", unit=Unit(id="UNI1", name="mL"))]
    updated = [_dc(sequence="1", unit=Unit(id="UNI2", name="L"))]

    patches, _, _ = generate_data_column_patches(initial, updated)

    assert len(patches) == 1
    assert isinstance(patches[0], DTPatchDatum)
    assert patches[0].attribute == "unit"
    assert patches[0].colId == "1"


def test_generate_data_column_patches_enum_change_populates_enum_patches_by_sequence():
    """Test that an ENUM column's option changes populate enum_patches, not a validation op."""
    initial_validation = [
        ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(id="E1", text="Low")])
    ]
    updated_validation = [
        ValueValidation(
            datatype=DataType.ENUM,
            value=[EnumValidationValue(id="E1", text="Low"), EnumValidationValue(text="High")],
        )
    ]
    initial = [_dc(sequence="1", validation=initial_validation)]
    updated = [_dc(sequence="1", validation=updated_validation)]

    patches, _, enum_patches = generate_data_column_patches(initial, updated)

    assert patches == []
    assert enum_patches == {"1": [{"operation": "add", "text": "High"}]}


def test_generate_data_column_patches_enum_newly_added_has_no_existing_options():
    """Test that introducing ENUM validation fresh diffs against an empty existing option set."""
    updated_validation = [
        ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(text="High")])
    ]
    initial = [_dc(sequence="1", validation=[])]
    updated = [_dc(sequence="1", validation=updated_validation)]

    _, _, enum_patches = generate_data_column_patches(initial, updated)

    assert enum_patches == {"1": [{"operation": "add", "text": "High"}]}


# ---------------------------------------------------------------------------
# generate_parameter_patches
# ---------------------------------------------------------------------------


def test_generate_parameter_patches_none_inputs_return_empty():
    """Test that None initial/updated parameters produce empty results."""
    patches, new_params, enum_patches = generate_parameter_patches(None, None)

    assert patches == []
    assert new_params == []
    assert enum_patches == {}


def test_generate_parameter_patches_unmatched_param_is_new():
    """Test that a parameter matching neither sequence nor id is classified as new."""
    patches, new_params, _ = generate_parameter_patches(
        initial_parameters=[], updated_parameters=[_pv(id="PRM9", sequence=None, value="x")]
    )

    assert patches == []
    assert len(new_params) == 1
    assert new_params[0].id == "PRM9"


def test_generate_parameter_patches_deleted_params_are_batched_into_one_op():
    """Test that all deleted parameters are batched into a single delete op.

    Unlike data columns (one delete op per sequence), parameters batch every
    deleted sequence into one oldValue list.
    """
    initial = [_pv(id="PRM1", sequence="1"), _pv(id="PRM2", sequence="2")]

    patches, _, _ = generate_parameter_patches(initial, [])

    assert patches == [
        PGPatchDatum(operation="delete", attribute="parameter", oldValue=["1", "2"])
    ]


def test_generate_parameter_patches_matches_by_id_and_adopts_initial_sequence():
    """Test that a param matched by id (no sequence set) is patched, not treated as new.

    The matched initial sequence is copied onto the caller's updated object so
    downstream code (and the caller) can rely on ``sequence`` being populated.
    """
    initial = [_pv(id="PRM1", sequence="10", value="a")]
    updated_param = _pv(id="PRM1", sequence=None, value="b")

    patches, new_params, _ = generate_parameter_patches(initial, [updated_param])

    assert new_params == []
    assert updated_param.sequence == "10"
    assert patches == [
        PGPatchDatum(operation="update", attribute="value", oldValue="a", newValue="b", rowId="10")
    ]


def test_generate_parameter_patches_field_changes_are_flat_not_grouped():
    """Test that unit/value/required changes are appended as separate flat ops."""
    initial = [_pv(id="PRM1", sequence="1", value="a", required=False)]
    updated = [
        _pv(
            id="PRM1",
            sequence="1",
            value="b",
            required=True,
            unit=Unit(id="UNI1", name="mL"),
        )
    ]

    patches, _, _ = generate_parameter_patches(initial, updated)

    attrs = {p.attribute for p in patches}
    assert attrs == {"unitId", "value", "required"}
    assert all(isinstance(p, PGPatchDatum) for p in patches)


def test_generate_parameter_patches_enum_change_skips_validation_op():
    """Test that an ENUM parameter's option changes populate enum_patches, not a validation op."""
    initial_validation = [
        ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(id="E1", text="Low")])
    ]
    updated_validation = [
        ValueValidation(
            datatype=DataType.ENUM,
            value=[EnumValidationValue(id="E1", text="Low"), EnumValidationValue(text="High")],
        )
    ]
    initial = [_pv(id="PRM1", sequence="1", validation=initial_validation)]
    updated = [_pv(id="PRM1", sequence="1", validation=updated_validation)]

    patches, _, enum_patches = generate_parameter_patches(initial, updated)

    assert [p for p in patches if p.attribute == "validation"] == []
    assert enum_patches == {"1": [{"operation": "add", "text": "High"}]}


def test_generate_parameter_patches_non_enum_validation_change_is_appended():
    """Test that a non-enum validation change is appended as a normal validation op."""
    initial = [
        _pv(id="PRM1", sequence="1", validation=[ValueValidation(datatype=DataType.NUMBER)])
    ]
    updated = [
        _pv(id="PRM1", sequence="1", validation=[ValueValidation(datatype=DataType.STRING)])
    ]

    patches, _, enum_patches = generate_parameter_patches(initial, updated)

    assert [p.attribute for p in patches] == ["validation"]
    assert enum_patches == {}


def test_generate_parameter_patches_datatype_switched_to_enum_skips_validation_op():
    """Test that switching a parameter's datatype to ENUM defers entirely to enum_patches.

    Even though the validation structure changed (not just the enum options),
    the general validation op is still suppressed once the new datatype is ENUM.
    """
    initial = [
        _pv(id="PRM1", sequence="1", validation=[ValueValidation(datatype=DataType.NUMBER)])
    ]
    updated = [
        _pv(
            id="PRM1",
            sequence="1",
            validation=[
                ValueValidation(datatype=DataType.ENUM, value=[EnumValidationValue(text="A")])
            ],
        )
    ]

    patches, _, enum_patches = generate_parameter_patches(initial, updated)

    assert [p.attribute for p in patches] == []
    assert enum_patches == {"1": [{"operation": "add", "text": "A"}]}


# ---------------------------------------------------------------------------
# handle_tags
# ---------------------------------------------------------------------------


def test_handle_tags_add_and_delete():
    """Test that added and removed tags each emit their own patch op."""
    existing = [Tag(id="T1", tag="a"), Tag(id="T2", tag="b")]
    updated = [Tag(id="T2", tag="b"), Tag(id="T3", tag="c")]

    patches = handle_tags(existing, updated)

    ops = {(p.operation, p.new_value or p.old_value) for p in patches}
    assert ops == {("add", "T3"), ("delete", "T1")}
    assert all(p.attribute == "tag" for p in patches)


def test_handle_tags_unchanged_emits_no_ops():
    """Test that identical tag lists emit no patch ops."""
    tags = [Tag(id="T1", tag="a")]
    assert handle_tags(tags, list(tags)) == []


def test_handle_tags_uses_custom_attribute_name():
    """Test that a custom attribute_name (e.g. 'tagId') is applied to every op."""
    patches = handle_tags([], [Tag(id="T1", tag="a")], attribute_name="tagId")

    assert patches[0].attribute == "tagId"


def test_handle_tags_none_lists_do_not_raise():
    """Test that None for either existing or updated tags behaves like an empty list."""
    assert handle_tags(None, None) == []


# ---------------------------------------------------------------------------
# generate_data_template_patches
# ---------------------------------------------------------------------------


def _data_template(**kwargs) -> DataTemplate:
    kwargs.setdefault("name", "T1")
    return DataTemplate(**kwargs)


def test_generate_data_template_patches_unset_columns_and_parameters_are_untouched():
    """Test that leaving data_column_values/parameter_values unset keeps them as-is.

    The diff falls back to the existing template's columns/parameters, so a
    caller who only changes e.g. ``name`` does not risk wiping the rest.
    """
    existing = _data_template(
        data_column_values=[_dc(sequence="1", value="10")],
        parameter_values=[_pv(id="PRM1", sequence="1", value="a")],
    )
    updated = _data_template(name="Renamed")

    result = generate_data_template_patches(
        PatchPayload(data=[]), updated_data_template=updated, existing_data_template=existing
    )
    general_patches, new_cols, dc_enum, new_params, p_enum, p_patches, acl_add, acl_delete = result

    assert new_cols == []
    assert new_params == []
    assert p_patches == []
    assert dc_enum == {}
    assert p_enum == {}


def test_generate_data_template_patches_acl_unset_emits_no_diff():
    """Test that leaving users_with_access unset does not diff the ACL at all."""
    existing = _data_template(users_with_access=[User.model_construct(id="U1")])
    updated = _data_template(name="Renamed")

    *_rest, acl_add, acl_delete = generate_data_template_patches(
        PatchPayload(data=[]), updated_data_template=updated, existing_data_template=existing
    )

    assert acl_add == []
    assert acl_delete == []


def test_generate_data_template_patches_acl_cleared_to_empty_deletes_all():
    """Test that explicitly clearing users_with_access to [] deletes every existing entry."""
    existing = _data_template(users_with_access=[User.model_construct(id="U1")])
    updated = _data_template(users_with_access=[])

    *_rest, acl_add, acl_delete = generate_data_template_patches(
        PatchPayload(data=[]), updated_data_template=updated, existing_data_template=existing
    )

    assert acl_add == []
    assert acl_delete == [{"id": "U1"}]


def test_generate_data_template_patches_acl_diff_adds_and_removes():
    """Test that a changed ACL emits the minimal set of adds and removes."""
    existing = _data_template(
        users_with_access=[User.model_construct(id="U1"), User.model_construct(id="U2")]
    )
    updated = _data_template(
        users_with_access=[User.model_construct(id="U2"), User.model_construct(id="U3")]
    )

    *_rest, acl_add, acl_delete = generate_data_template_patches(
        PatchPayload(data=[]), updated_data_template=updated, existing_data_template=existing
    )

    assert acl_add == [{"id": "U3"}]
    assert acl_delete == [{"id": "U1"}]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: generate_data_template_patches passes updated_data_template.tags "
        "straight to handle_tags (src/albert/utils/_patch.py:652-656) with no "
        "unset guard, so an unset tags field deletes every existing tag even "
        "though update()'s docstring Notes never list tags as updatable."
    ),
)
def test_generate_data_template_patches_tags_left_unset_is_not_touched():
    """Test that leaving tags unset on the updated template does not delete existing tags."""
    existing = _data_template(tags=[Tag(id="TAG1", tag="a")])
    updated = _data_template(name="Renamed")

    general_patches, *_rest = generate_data_template_patches(
        PatchPayload(data=[]), updated_data_template=updated, existing_data_template=existing
    )

    assert general_patches.data == []


# ---------------------------------------------------------------------------
# build_acl_patch_payload
# ---------------------------------------------------------------------------


def test_build_acl_patch_payload_empty_values_returns_none():
    """Test that an empty values list produces no payload at all."""
    assert build_acl_patch_payload(operation="add", values=[]) is None


def test_build_acl_patch_payload_add():
    """Test that an add operation carries new_value and omits old_value."""
    payload = build_acl_patch_payload(operation="add", values=[{"id": "U1"}])

    assert payload == GeneralPatchPayload(
        data=[GeneralPatchDatum(attribute="ACL", operation="add", newValue=[{"id": "U1"}])]
    )


def test_build_acl_patch_payload_delete():
    """Test that a delete operation carries old_value and omits new_value."""
    payload = build_acl_patch_payload(operation="delete", values=[{"id": "U1"}])

    assert payload == GeneralPatchPayload(
        data=[GeneralPatchDatum(attribute="ACL", operation="delete", oldValue=[{"id": "U1"}])]
    )


# ---------------------------------------------------------------------------
# generate_parameter_group_patches
# ---------------------------------------------------------------------------


def _parameter_group(**kwargs) -> ParameterGroup:
    kwargs.setdefault("name", "PG1")
    return ParameterGroup(**kwargs)


def test_generate_parameter_group_patches_appends_parameter_and_tag_ops():
    """Test that parameter and tag diffs are appended onto the initial patch payload."""
    existing = _parameter_group(
        parameters=[_pv(id="PRM1", sequence="1", value="a")],
        tags=[Tag(id="TAG1", tag="old")],
    )
    updated = _parameter_group(
        type=PGType.BATCH,
        parameters=[_pv(id="PRM1", sequence="1", value="b")],
        tags=[Tag(id="TAG2", tag="new")],
    )
    seed = PatchPayload(
        data=[PGPatchDatum(operation="update", attribute="name", oldValue="PG1", newValue="PG1x")]
    )

    general_patches, new_params, enum_patches = generate_parameter_group_patches(
        initial_patches=seed, updated_parameter_group=updated, existing_parameter_group=existing
    )

    assert new_params == []
    assert enum_patches == {}
    attrs = [p.attribute for p in general_patches.data]
    assert "name" in attrs  # the seeded patch is preserved
    assert "value" in attrs  # from the parameter diff
    assert "tagId" in attrs  # tags use "tagId" for parameter groups, not "tag"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: generate_parameter_group_patches passes updated_parameter_group.tags "
        "straight to handle_tags (src/albert/utils/_patch.py:879-883) with no "
        "unset guard, so an unset tags field deletes every existing tag even "
        "though update()'s docstring Notes never list tags as updatable."
    ),
)
def test_generate_parameter_group_patches_tags_left_unset_is_not_touched():
    """Test that leaving tags unset on the updated group does not delete existing tags."""
    existing = _parameter_group(tags=[Tag(id="TAG1", tag="a")])
    updated = _parameter_group(name="Renamed")

    general_patches, *_rest = generate_parameter_group_patches(
        initial_patches=PatchPayload(data=[]),
        updated_parameter_group=updated,
        existing_parameter_group=existing,
    )

    assert general_patches.data == []
