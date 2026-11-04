"""Unit tests for AttributeCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_attribute_patch_payload`` (reference
names are add/update only, unit assignment is set-once, formulas are one
whole-list op) and the ``_check_formulas`` field rules, with no I/O to fake.
``get_by_ids`` chunking is covered with ``responses`` since those tests only
assert on the requests the SDK sends.
"""

import re
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from albert.collections.attributes import AttributeCollection
from albert.core.shared.models.base import EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.resources.attributes import (
    Attribute,
    AttributeParameterItem,
    ExpressionType,
    FormulaMetadata,
    ValidationItem,
)
from albert.resources.parameter_groups import DataType, Operator
from tests.unit.conftest import UNIT_BASE_URL

_IDS_URL = f"{UNIT_BASE_URL}/api/v3/attributes/ids"


def test_unset_reference_name_emits_no_op(offline_session) -> None:
    """Test that an unset reference_name produces no patch operation."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1")  # reference_name never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_none_reference_name_does_not_delete(offline_session) -> None:
    """Test that explicitly clearing reference_name to None emits no op.

    reference_name must remain unique and is add/update only per the update()
    Notes; the builder never emits a delete for it.
    """
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute.model_construct(id="ATR1", reference_name=None)

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_new_reference_name_emits_add_op(offline_session) -> None:
    """Test that setting reference_name where none existed emits an add op."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 25C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "referenceName"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "Viscosity @ 25C"


def test_changed_reference_name_emits_update_op(offline_session) -> None:
    """Test that changing an existing reference_name emits an update op with the old value."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 30C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "referenceName"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "Viscosity @ 25C"
    assert payload.data[0].new_value == "Viscosity @ 30C"


def test_unchanged_reference_name_emits_no_op(offline_session) -> None:
    """Test that setting reference_name to its existing value emits no op."""
    existing = Attribute(id="ATR1", reference_name="Viscosity @ 25C")
    updated = Attribute(id="ATR1", reference_name="Viscosity @ 25C")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_unset_validation_emits_no_op(offline_session) -> None:
    """Test that unset validation produces no patch operation."""
    existing = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1)])
    updated = Attribute(id="ATR1")  # validation never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_changed_validation_emits_full_list_update(offline_session) -> None:
    """Test that changed validation rules emit a whole-list update op."""
    existing = Attribute(
        id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1, max=10)]
    )
    updated = Attribute(
        id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=0, max=10)]
    )

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "validation"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["min"] == 1
    assert payload.data[0].new_value[0]["min"] == 0


def test_unchanged_validation_emits_no_op(offline_session) -> None:
    """Test that equivalent validation rules (new instances, same values) emit no op."""
    existing = Attribute(
        id="ATR1",
        validation=[
            ValidationItem(datatype=DataType.NUMBER, min=1, max=10, operator=Operator.BETWEEN)
        ],
    )
    updated = Attribute(
        id="ATR1",
        validation=[
            ValidationItem(datatype=DataType.NUMBER, min=1, max=10, operator=Operator.BETWEEN)
        ],
    )

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_skip_validation_bypasses_changed_validation(offline_session) -> None:
    """Test that skip_validation=True omits the validation diff even when it changed.

    Used when the caller already applied the change via the enum-specific PUT
    endpoint, to avoid sending the same change twice.
    """
    existing = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=1)])
    updated = Attribute(id="ATR1", validation=[ValidationItem(datatype=DataType.NUMBER, min=2)])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated, skip_validation=True
    )

    assert payload.data == []


def test_unset_parameters_emits_no_op(offline_session) -> None:
    """Test that unset parameters produce no patch operation."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1")  # parameters never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_changed_parameters_emits_full_list_update(offline_session) -> None:
    """Test that changed parameter setpoints emit a whole-list update op."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="30")])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "parameters"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["value"] == "25"
    assert payload.data[0].new_value[0]["value"] == "30"


def test_unchanged_parameters_emits_no_op(offline_session) -> None:
    """Test that equivalent parameter setpoints emit no op."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_parameters_cleared_to_empty_list_emits_update(offline_session) -> None:
    """Test that clearing parameters to [] is an update (never a silent no-op)."""
    existing = Attribute(id="ATR1", parameters=[AttributeParameterItem(id="PRM1", value="25")])
    updated = Attribute(id="ATR1", parameters=[])

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "parameters"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value[0]["value"] == "25"
    assert payload.data[0].new_value == []


def test_unit_id_added_when_no_existing_unit(offline_session) -> None:
    """Test that assigning a unit_id when none is set emits an add op."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", unit_id="UNI1")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "unitId"
    assert payload.data[0].operation == PatchOperation.ADD
    assert payload.data[0].new_value == "UNI1"


def test_unit_id_ignored_once_a_unit_is_already_assigned(offline_session) -> None:
    """Test that unit_id is set-once: no op is emitted once a unit is assigned."""
    existing = Attribute(id="ATR1", unit=EntityLinkWithName(id="UNI1", name="cP"))
    updated = Attribute(id="ATR1", unit_id="UNI2")

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_unset_unit_id_emits_no_op(offline_session) -> None:
    """Test that an unset unit_id produces no patch operation."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1")  # unit_id never set

    payload = AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


# --- formula_metadata ---


def _ib(**overrides) -> FormulaMetadata:
    fields = {
        "display_name": "Solids Share",
        "expression": "wt% / sum(wt%) * [ATR45]",
        "expression_type": ExpressionType.INGREDIENT_BASIS,
        "request_inverse": False,
    }
    return FormulaMetadata(**{**fields, **overrides})


def _cp(**overrides) -> FormulaMetadata:
    fields = {
        "display_name": "Total Solids",
        "expression": "sum(ingredient_basis)",
        "expression_type": ExpressionType.CALCULATED_PROPERTY,
        "request_inverse": False,
    }
    return FormulaMetadata(**{**fields, **overrides})


_IB_WIRE = {
    "displayName": "Solids Share",
    "expression": "wt% / sum(wt%) * [ATR45]",
    "expressionType": "INGREDIENT_BASIS",
    "requestInverse": False,
}
_CP_WIRE = {
    "displayName": "Total Solids",
    "expression": "sum(ingredient_basis)",
    "expressionType": "CALCULATED_PROPERTY",
    "requestInverse": False,
}


def _patch_dump(*, existing: Attribute, updated: Attribute, session) -> dict:
    payload = AttributeCollection(session=session)._generate_attribute_patch_payload(
        existing=existing, updated=updated
    )
    return payload.model_dump(by_alias=True, mode="json")


def test_unset_formula_metadata_emits_no_op(offline_session) -> None:
    """Test that unset formula_metadata leaves existing formulas untouched."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib()])
    updated = Attribute(id="ATR1")  # formula_metadata never set

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {"data": []}


def test_empty_formula_metadata_emits_root_delete(offline_session) -> None:
    """Test that [] removes every existing formula with one root delete."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])
    updated = Attribute(id="ATR1", formula_metadata=[])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {"data": [{"operation": "delete", "attribute": "formulaMetadata"}]}


def test_none_formula_metadata_leaves_existing_formulas(offline_session) -> None:
    """Test that an explicit None keeps existing formulas and emits no op."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])
    updated = Attribute(id="ATR1", formula_metadata=None)

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {"data": []}


@pytest.mark.parametrize("cleared", [None, []], ids=["none", "empty-list"])
def test_cleared_formula_metadata_emits_no_op_when_none_exist(offline_session, cleared) -> None:
    """Test that clearing formulas on an attribute without any emits no op."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", formula_metadata=cleared)

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {"data": []}


def test_first_formulas_emit_root_add_with_full_list(offline_session) -> None:
    """Test that formulas on an attribute without any are sent as one root add."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [
            {"operation": "add", "attribute": "formulaMetadata", "newValue": [_IB_WIRE, _CP_WIRE]}
        ]
    }


def test_appended_formula_emits_root_update_with_full_list(offline_session) -> None:
    """Test that adding a formula to existing ones replaces the whole list, keeping the rest."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib()])
    updated = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [
            {
                "operation": "update",
                "attribute": "formulaMetadata",
                "newValue": [_IB_WIRE, _CP_WIRE],
            }
        ]
    }


def test_renamed_formula_emits_root_update_with_full_list(offline_session) -> None:
    """Test that renaming one formula sends the full list with the new name."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])
    updated = Attribute(id="ATR1", formula_metadata=[_ib(), _cp(display_name="Solids")])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [
            {
                "operation": "update",
                "attribute": "formulaMetadata",
                "newValue": [_IB_WIRE, {**_CP_WIRE, "displayName": "Solids"}],
            }
        ]
    }


def test_removed_formula_emits_root_update_with_remaining_list(offline_session) -> None:
    """Test that leaving one formula out sends only the formulas that remain."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])
    updated = Attribute(id="ATR1", formula_metadata=[_ib()])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [{"operation": "update", "attribute": "formulaMetadata", "newValue": [_IB_WIRE]}]
    }


def test_unchanged_formula_metadata_emits_no_op(offline_session) -> None:
    """Test that an equal formula list (new instances, same values) emits no op."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])
    updated = Attribute(id="ATR1", formula_metadata=[_ib(), _cp()])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {"data": []}


def test_formula_display_names_are_trimmed(offline_session) -> None:
    """Test that surrounding whitespace in a display name is removed before sending."""
    existing = Attribute(id="ATR1")
    updated = Attribute(id="ATR1", formula_metadata=[_ib(display_name="  Solids Share ")])

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [{"operation": "add", "attribute": "formulaMetadata", "newValue": [_IB_WIRE]}]
    }


def test_fetched_attribute_with_other_change_emits_no_formula_op(offline_session) -> None:
    """Test that a fetched attribute edited elsewhere sends no formula op, even with rule-breaking formulas."""
    raw = {
        "albertId": "ATR1",
        "referenceName": "Solids",
        "formulaMetadata": [
            {**_CP_WIRE, "requestInverse": True},
            {**_CP_WIRE, "displayName": "Total Solids 2"},
        ],
    }
    existing = Attribute.model_validate(raw)
    updated = Attribute.model_validate(raw)
    updated.reference_name = "Solids Content"

    dumped = _patch_dump(existing=existing, updated=updated, session=offline_session)

    assert dumped == {
        "data": [
            {
                "operation": "update",
                "attribute": "referenceName",
                "oldValue": "Solids",
                "newValue": "Solids Content",
            }
        ]
    }


def test_changed_formula_metadata_raises_on_field_rule(offline_session) -> None:
    """Test that a changed formula list breaking a field rule raises before anything is sent."""
    existing = Attribute(id="ATR1", formula_metadata=[_ib()])
    updated = Attribute(id="ATR1", formula_metadata=[_ib(), _cp(request_inverse=True)])

    with pytest.raises(ValueError, match="request_inverse=True on CALCULATED_PROPERTY"):
        AttributeCollection(session=offline_session)._generate_attribute_patch_payload(
            existing=existing, updated=updated
        )


# --- _check_formulas ---


@pytest.mark.parametrize(
    "formulas",
    [
        pytest.param([], id="empty"),
        pytest.param([_ib()], id="one-ib"),
        pytest.param([_cp()], id="one-cp"),
        pytest.param([_ib(request_inverse=True), _cp()], id="ib-back-solve-and-cp"),
        pytest.param([_cp(expression="sum(wt% * [Viscosity]) / sum(wt%)")], id="name-reference"),
        pytest.param(
            [_cp(expression='sum(wt% WHERE Function = Core AND Function = "Shell")')],
            id="malformed-where",
        ),
    ],
)
def test_check_formulas_accepts(formulas) -> None:
    """Test that formulas within the field rules pass, whatever their expressions say."""
    AttributeCollection._check_formulas(formulas)


@pytest.mark.parametrize(
    ("formulas", "fragment"),
    [
        pytest.param(
            [_ib(), _ib(display_name="PHR")],
            "more than one INGREDIENT_BASIS (Solids Share, PHR)",
            id="two-ib",
        ),
        pytest.param(
            [_cp(), _cp(display_name="Density")],
            "more than one CALCULATED_PROPERTY (Total Solids, Density)",
            id="two-cp",
        ),
        pytest.param(
            [_cp(request_inverse=True)],
            "request_inverse=True on CALCULATED_PROPERTY (Total Solids)",
            id="cp-back-solve",
        ),
    ],
)
def test_check_formulas_rejects(formulas, fragment) -> None:
    """Test that formulas breaking a field rule raise with a message naming the rule."""
    with pytest.raises(ValueError, match=re.escape(fragment)):
        AttributeCollection._check_formulas(formulas)


def test_check_formulas_reports_every_problem_at_once() -> None:
    """Test that several broken rules are reported together in one error."""
    formulas = [_cp(request_inverse=True), _cp(display_name="Density")]

    with pytest.raises(ValueError) as excinfo:
        AttributeCollection._check_formulas(formulas)

    assert str(excinfo.value).startswith(
        "Invalid formula_metadata: more than one CALCULATED_PROPERTY (Total Solids, Density); "
        "request_inverse=True on CALCULATED_PROPERTY (Total Solids); "
    )


# --- get_by_ids chunking ---


def _sent_id_batches() -> list[list[str]]:
    return [parse_qs(urlparse(call.request.url).query)["id"] for call in responses.calls]


@responses.activate
def test_get_by_ids_chunks_ids_into_groups_of_300(offline_session) -> None:
    """Test that an ID list longer than 300 is split into lookups of at most 300 IDs."""
    responses.get(_IDS_URL, json={"items": []})
    ids = [f"ATR{i}" for i in range(650)]

    result = AttributeCollection(session=offline_session).get_by_ids(ids=ids)

    assert result == []
    assert _sent_id_batches() == [ids[:300], ids[300:600], ids[600:]]


@responses.activate
def test_get_by_ids_omits_batches_with_no_matches(offline_session) -> None:
    """Test that a chunk matching no attributes contributes nothing to the result."""
    responses.get(_IDS_URL, json={"items": [{"albertId": "ATR0"}]})
    responses.get(_IDS_URL, status=404, json={"message": "Attributes not found"})
    ids = [f"ATR{i}" for i in range(301)]

    result = AttributeCollection(session=offline_session).get_by_ids(ids=ids)

    assert [a.id for a in result] == ["ATR0"]
    assert len(responses.calls) == 2


@responses.activate
def test_get_by_ids_sends_no_lookup_for_empty_ids(offline_session) -> None:
    """Test that an empty ID list returns an empty result without any lookup."""
    result = AttributeCollection(session=offline_session).get_by_ids(ids=[])

    assert result == []
    assert len(responses.calls) == 0
