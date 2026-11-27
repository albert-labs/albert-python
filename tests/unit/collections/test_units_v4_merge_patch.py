"""Unit tests for pure v4 unit and unit-family payload helpers."""

import pytest

from albert.collections.unit_families_v4 import UnitFamilyV4Collection
from albert.collections.units_v4 import UnitV4Collection
from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type
from albert.resources.units_v4 import UnitFamilyV4Ref, UnitV4, UnitV4Type


def _existing_unit(**overrides) -> UnitV4:
    data = {
        "id": "UNI1",
        "name": "Grams",
        "description": "Grams weight",
        "type": "Convertible",
        "symbol": "g",
        "synonyms": ["g", "grms"],
        "siUnit": "kg",
        "siValue": "0.001",
        "unitFamilies": [{"familyId": "UNF1", "familyName": "Mass"}],
    }
    data.update(overrides)
    return UnitV4.model_validate(data)


# --- UnitV4Collection._generate_create_payload ---


def test_unit_create_payload_sends_family_ids():
    """Test that a create payload contains writable fields and family IDs."""
    unit = UnitV4(
        name="Batch",
        symbol="batch",
        type=UnitV4Type.NON_CONVERTIBLE,
        unit_families=[UnitFamilyV4Ref(id="UNF3")],
    )

    payload = UnitV4Collection._generate_create_payload(unit=unit)

    assert payload == {
        "name": "Batch",
        "type": "Non-Convertible",
        "symbol": "batch",
        "unitFamilies": ["UNF3"],
    }


def test_unit_create_payload_requires_symbol():
    """Test that create rejects a unit whose symbol is absent."""
    unit = UnitV4(name="Grams", type=UnitV4Type.CONVERTIBLE, ref_unit="g")

    with pytest.raises(ValueError, match="non-empty symbol"):
        UnitV4Collection._generate_create_payload(unit=unit)


@pytest.mark.parametrize("symbol", ["", "   "], ids=["empty", "whitespace"])
def test_unit_create_payload_rejects_blank_symbol(symbol: str):
    """Test that create rejects a blank unit symbol."""
    unit = UnitV4(name="Grams", symbol=symbol, type=UnitV4Type.CONVERTIBLE, ref_unit="g")

    with pytest.raises(ValueError, match="non-empty symbol"):
        UnitV4Collection._generate_create_payload(unit=unit)


# --- UnitV4Collection._generate_setup_payload ---


def test_unit_setup_payload_includes_full_convertible_unit():
    """Test that convertible setup includes the complete unit and reference fields."""
    unit = UnitV4(
        id="UNI1",
        name="Grams",
        description="Grams weight",
        symbol="g",
        synonyms=["g", "grms"],
        type=UnitV4Type.CONVERTIBLE,
        ref_unit="lb",
        ref_unit_value="0.00220462",
        unit_families=[UnitFamilyV4Ref(id="UNF9")],
    )

    payload = UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")

    assert payload == {
        "id": "UNI1",
        "name": "Grams",
        "description": "Grams weight",
        "type": "Convertible",
        "symbol": "g",
        "synonyms": ["g", "grms"],
        "refUnit": "lb",
        "refUnitValue": "0.00220462",
        "unitFamilyId": "UNF1",
    }


def test_unit_setup_payload_supports_reference_expression():
    """Test that convertible setup can use a reference expression."""
    unit = UnitV4(
        id="UNI1",
        name="Kilograms",
        symbol="kg",
        type=UnitV4Type.CONVERTIBLE,
        ref_unit_exp="1000*g",
    )

    payload = UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")

    assert payload == {
        "id": "UNI1",
        "name": "Kilograms",
        "type": "Convertible",
        "symbol": "kg",
        "refUnitExp": "1000*g",
        "unitFamilyId": "UNF1",
    }


def test_unit_setup_payload_includes_non_convertible_families():
    """Test that non-convertible setup includes family IDs and excludes reference fields."""
    unit = UnitV4(
        id="UNI1",
        name="Pieces",
        description="Individual pieces",
        symbol="pcs",
        synonyms=["piece"],
        type=UnitV4Type.NON_CONVERTIBLE,
        ref_unit="g",
        ref_unit_exp="1000*g",
        ref_unit_value="1000",
        unit_families=[UnitFamilyV4Ref(id="UNF1"), UnitFamilyV4Ref(id="UNF2")],
    )

    payload = UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")

    assert payload == {
        "id": "UNI1",
        "name": "Pieces",
        "description": "Individual pieces",
        "type": "Non-Convertible",
        "symbol": "pcs",
        "synonyms": ["piece"],
        "unitFamilies": ["UNF1", "UNF2"],
        "unitFamilyId": "UNF1",
    }


def test_unit_setup_payload_requires_id():
    """Test that setup rejects a unit whose ID is absent."""
    unit = UnitV4(name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE, ref_unit="g")

    with pytest.raises(ValueError, match="must have an id"):
        UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")


def test_unit_setup_payload_requires_symbol():
    """Test that setup rejects a unit whose symbol is absent."""
    unit = UnitV4(id="UNI1", name="Grams", type=UnitV4Type.CONVERTIBLE, ref_unit="g")

    with pytest.raises(ValueError, match="non-empty symbol"):
        UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")


@pytest.mark.parametrize("symbol", ["", "   "], ids=["empty", "whitespace"])
def test_unit_setup_payload_rejects_blank_symbol(symbol: str):
    """Test that setup rejects a blank unit symbol."""
    unit = UnitV4(
        id="UNI1", name="Grams", symbol=symbol, type=UnitV4Type.CONVERTIBLE, ref_unit="g"
    )

    with pytest.raises(ValueError, match="non-empty symbol"):
        UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")


def test_unit_setup_payload_requires_type():
    """Test that setup rejects a unit whose type is absent."""
    unit = UnitV4(id="UNI1", name="Grams", symbol="g", ref_unit="g")

    with pytest.raises(ValueError, match="must have a type"):
        UnitV4Collection._generate_setup_payload(unit=unit, unit_family_id="UNF1")


# --- UnitV4Collection._generate_merge_patch ---


def test_unit_patch_sends_only_changed_fields():
    """Test that only fields the caller set and changed are included."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.description = "Grams, for powders"
    updated.synonyms = ["g", "gram"]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"description": "Grams, for powders", "synonyms": ["g", "gram"]}


def test_unit_patch_leaves_unset_fields_untouched():
    """Test that a partial update never emits fields the caller did not set."""
    existing = _existing_unit()
    updated = UnitV4(id="UNI1", name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE)

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {}


def test_unit_patch_explicit_none_clears_description():
    """Test that an explicit ``None`` clears the description."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.description = None

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"description": None}


def test_unit_patch_families_on_non_convertible_sends_ids():
    """Test that non-convertible family changes contain a plain list of IDs."""
    existing = _existing_unit(type="Non-Convertible", siUnit=None, siValue=None)
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF1"), UnitFamilyV4Ref(id="UNF9")]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"unitFamilies": ["UNF1", "UNF9"]}


def test_unit_patch_families_same_set_is_noop():
    """Test that reordering families without changing membership emits nothing."""
    existing = _existing_unit(
        type="Non-Convertible",
        unitFamilies=[
            {"familyId": "UNF1", "familyName": "A"},
            {"familyId": "UNF2", "familyName": "B"},
        ],
    )
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF2"), UnitFamilyV4Ref(id="UNF1")]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {}


def test_unit_patch_families_on_convertible_raises():
    """Test that changing families on a convertible unit raises."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF9")]

    with pytest.raises(ValueError, match="non-convertible"):
        UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)


def test_unit_patch_legacy_unit_directs_to_setup():
    """Test that a legacy unit with no type is directed to setup instead of updated."""
    existing = _existing_unit(
        type=None, siUnit=None, siValue=None, unitFamilies=[], origin="Custom (Legacy)"
    )
    updated = existing.model_copy()
    updated.description = "New description"

    with pytest.raises(ValueError, match=r"setup\(\)"):
        UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)


@pytest.mark.parametrize(
    "new_type",
    [UnitV4Type.NON_CONVERTIBLE, None],
    ids=["changed", "cleared"],
)
def test_unit_patch_type_change_after_setup_raises(new_type: UnitV4Type | None):
    """Test that the type of a set-up unit cannot be changed or cleared."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.type = new_type

    with pytest.raises(ValueError, match="type"):
        UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("ref_unit", "kg"),
        ("ref_unit_exp", "1000*g"),
        ("ref_unit_value", "1000"),
    ],
)
def test_unit_patch_si_mapping_change_after_setup_raises(attribute: str, value: str):
    """Test that SI mapping changes on a set-up unit are rejected."""
    existing = _existing_unit()
    updated = existing.model_copy()
    setattr(updated, attribute, value)

    with pytest.raises(ValueError, match="SI mapping"):
        UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)


# --- UnitFamilyV4Collection._generate_merge_patch ---


def test_unit_family_patch_sends_only_name_and_description():
    """Test that only name and description are patchable on a unit family."""
    existing = UnitFamilyV4.model_validate(
        {"id": "UNF1", "name": "Mass", "description": "Old", "type": "Convertible"}
    )
    updated = existing.model_copy()
    updated.name = "Mass (SI)"
    updated.description = "Old"

    patch = UnitFamilyV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"name": "Mass (SI)"}

    untouched = UnitFamilyV4(id="UNF1", name="Mass", type=UnitFamilyV4Type.CONVERTIBLE)
    assert UnitFamilyV4Collection._generate_merge_patch(existing=existing, updated=untouched) == {}
