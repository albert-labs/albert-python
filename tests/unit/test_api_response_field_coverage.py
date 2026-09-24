"""Guard that models keep the API response fields their consumers depend on.

``BaseAlbertModel`` does not set an ``extra`` policy, so Pydantic defaults to
``extra="ignore"`` and any field a model fails to declare is dropped at validation
and is not recoverable from ``model_extra``. These tests pin the fields that were
silently lost, using payload fragments recorded from the live API.
"""

import pytest

from albert.resources.product_design import (
    CasLevelSubstance,
    UnpackedCasInfo,
    UnpackedProductDesign,
)
from albert.resources.substance_v4 import SubstanceV4Info, SubstanceV4SearchItem
from albert.resources.unit_families_v4 import (
    UnitFamilyV4,
    UnitFamilyV4Lookup,
    UnitFamilyV4Origin,
    UnitFamilyV4SearchItem,
    UnitFamilyV4Type,
)
from albert.resources.units_v4 import (
    UnitFamilyV4Ref,
    UnitV4,
    UnitV4Compatible,
    UnitV4Lookup,
    UnitV4Origin,
    UnitV4Type,
)

# Recorded from GET /api/v3/productdesign/DESIGN/unpack?formulaId=INVP603-004
CAS_LEVEL_SUBSTANCE_PAYLOAD = {
    "casPrimaryKeyId": "CAS39928",
    "casID": "68585-34-2",
    "amount": 0.24642857,
    "min": 0.19714286,
    "aggregatedFunc": [],
    "target": 0,
    "albertId": "INVA42942",
    "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b",
}


def test_cas_level_substance_keeps_substance_id():
    """The Regulatory DB key must survive validation, not be dropped as an extra."""
    substance = CasLevelSubstance.model_validate(CAS_LEVEL_SUBSTANCE_PAYLOAD)

    assert substance.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    assert substance.cas_id == "68585-34-2"
    assert substance.albert_id == "INVA42942"
    assert substance.min == pytest.approx(0.19714286)
    assert substance.target == pytest.approx(0)


def test_unpacked_product_design_exposes_substance_ids():
    """substance_id survives through the top-level unpack response model."""
    unpacked = UnpackedProductDesign.model_validate(
        {"casLevelSubstances": [CAS_LEVEL_SUBSTANCE_PAYLOAD]}
    )

    assert unpacked.cas_level_substances is not None
    assert unpacked.cas_level_substances[0].substance_id == (
        "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    )


def test_unpacked_cas_info_keeps_substance_id():
    cas_info = UnpackedCasInfo.model_validate(
        {"id": "CAS39928", "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"}
    )

    assert cas_info.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"


def test_substance_v4_info_declares_wgk():
    """``SubstanceV4Info`` must expose WGK as a typed field, matching its search sibling.

    Only ``region="DE"`` returns the field; the models must agree on the attribute
    name so callers do not need to know which endpoint produced the record.
    """
    info = SubstanceV4Info.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})
    search_item = SubstanceV4SearchItem.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})

    assert info.wgk == "WGK 1"
    assert search_item.wgk == "WGK 1"


def test_substance_v4_info_wgk_absent_outside_german_region():
    """Regions other than DE omit WGK; the model must not invent a value."""
    info = SubstanceV4Info.model_validate({"casID": "64-18-6"})

    assert info.wgk is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pdscl", {"maxValue": 1, "unit": "%"}),
        (
            "prtr",
            {
                "className": "Specified Class 1,Class 1",
                "unit": "%",
                "controlNumber": 411,
                "maxValue": 0.1,
            },
        ),
    ],
)
def test_substance_v4_info_accepts_japanese_object_fields(field, value):
    """``region="JP"`` returns objects for these; typing them as ``str`` raised."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0", field: value})

    assert getattr(info, field) == value


# Payloads below mirror the Swagger examples published by the master-data service
# (invent-core services/master-data/src/units/examples, unit-families/examples).
_AUDIT = {"at": "2024-01-15T10:30:00.000Z", "by": "user-uuid-123", "byName": "Jane Smith"}

UNIT_V4_CONVERTIBLE_PAYLOAD = {
    "id": "3643d5a5-32c1-43c3-9f3e-aea810d21fc9",
    "name": "Grams",
    "description": "Grams weight",
    "type": "Convertible",
    "symbol": "g",
    "synonyms": ["g", "grms"],
    "siUnit": "kg",
    "siValue": "0.001",
    "refUnit": "lb",
    "refUnitExp": None,
    "refUnitValue": "0.00220462",
    "status": "active",
    "origin": "Custom",
    "unitFamilies": [{"familyId": "UNF1", "familyName": "Mass"}],
    "created": _AUDIT,
    "updated": _AUDIT,
}

UNIT_FAMILY_V4_PAYLOAD = {
    "id": "UNF1",
    "name": "Mass",
    "description": "Units of mass measurement",
    "type": "Convertible",
    "siUnit": "kg",
    "dimension": "Mass",
    "origin": "Albert Managed",
    "status": "active",
    "units": ["kg", "g", "mg", "lb", "oz"],
    "sameSiBasisFamilies": [],
    "created": _AUDIT,
    "updated": _AUDIT,
}


def test_unit_v4_keeps_full_convertible_record():
    """Every documented field on a convertible unit survives validation."""
    unit = UnitV4.model_validate(UNIT_V4_CONVERTIBLE_PAYLOAD)

    assert unit.id == "3643d5a5-32c1-43c3-9f3e-aea810d21fc9"
    assert unit.type is UnitV4Type.CONVERTIBLE
    assert unit.origin is UnitV4Origin.CUSTOM
    assert unit.si_unit == "kg"
    assert unit.si_value == "0.001"
    assert unit.ref_unit == "lb"
    assert unit.ref_unit_exp is None
    assert unit.ref_unit_value == "0.00220462"
    assert unit.unit_families == [UnitFamilyV4Ref(id="UNF1", name="Mass")]
    assert unit.created is not None and unit.created.by_name == "Jane Smith"
    assert unit.updated is not None


def test_unit_v4_accepts_non_convertible_and_search_shapes():
    """Non-convertible records omit SI fields; search hits omit ``updated``."""
    unit = UnitV4.model_validate(
        {
            "id": "4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d",
            "name": "Batch",
            "type": "Non-Convertible",
            "symbol": "batch",
            "status": "active",
            "origin": "Custom (Legacy)",
            "unitFamilies": [{"familyId": "UNF3", "familyName": "Count"}],
            "created": _AUDIT,
        }
    )

    assert unit.type is UnitV4Type.NON_CONVERTIBLE
    assert unit.origin is UnitV4Origin.CUSTOM_LEGACY
    assert unit.si_unit is None
    assert unit.updated is None


def test_unit_v4_create_payload_sends_family_ids_only():
    """The create body carries family IDs and no read-only fields."""
    unit = UnitV4(
        name="Batch",
        symbol="batch",
        type=UnitV4Type.NON_CONVERTIBLE,
        unit_families=[UnitFamilyV4Ref(id="UNF3")],
    )
    payload = unit.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert payload["type"] == "Non-Convertible"
    assert payload["unitFamilies"] == [{"id": "UNF3"}]
    assert "siUnit" not in payload
    assert "status" not in payload


def test_unit_v4_lookup_and_compatible_shapes():
    """Lookup and compatible responses map their camelCase keys."""
    lookup = UnitV4Lookup.model_validate(
        {
            "exists": False,
            "similarMatches": [{"id": "b2c3", "name": "Megapascal", "symbol": "MPa"}],
        }
    )
    assert lookup.exists is False
    assert lookup.similar_matches[0].symbol == "MPa"

    compatible = UnitV4Compatible.model_validate(
        {
            "refUnit": "g",
            "siUnit": "kg",
            "siValue": "0.001",
            "refUnitValue": "1000",
            "unitFamilies": [{"familyId": "UNF1", "familyName": "Mass"}],
            "dimension": "Mass",
        }
    )
    assert compatible.ref_unit_value == "1000"
    assert compatible.dimension == "Mass"
    assert compatible.unit_families[0].name == "Mass"


def test_unit_family_v4_ref_accepts_both_wire_spellings():
    """Units endpoints send ``familyId``/``familyName``; the ``id``/``name`` spelling
    stays accepted, and serialization keeps the ``id``/``name`` keys."""
    by_id = UnitFamilyV4Ref.model_validate({"id": "UNF1", "name": "Mass"})
    by_family = UnitFamilyV4Ref.model_validate({"familyId": "UNF1", "familyName": "Mass"})

    assert by_id == by_family == UnitFamilyV4Ref(id="UNF1", name="Mass")
    assert by_family.model_dump(by_alias=True, mode="json") == {"id": "UNF1", "name": "Mass"}


def test_unit_family_v4_keeps_full_record():
    """Every documented field on a unit family survives validation."""
    family = UnitFamilyV4.model_validate(UNIT_FAMILY_V4_PAYLOAD)

    assert family.type is UnitFamilyV4Type.CONVERTIBLE
    assert family.origin is UnitFamilyV4Origin.ALBERT_MANAGED
    assert family.si_unit == "kg"
    assert family.dimension == "Mass"
    assert family.units == ["kg", "g", "mg", "lb", "oz"]
    assert family.same_si_basis_families == []
    assert family.created is not None and family.created.at is not None

    non_convertible = UnitFamilyV4.model_validate(
        {**UNIT_FAMILY_V4_PAYLOAD, "id": "UNF3", "type": "Non-Convertible", "siUnit": None}
    )
    assert non_convertible.si_unit is None


def test_unit_family_v4_search_item_and_lookup_shapes():
    """Search hits omit the computed fields; lookup maps ``similarMatches``."""
    search_item = UnitFamilyV4SearchItem.model_validate(
        {
            "id": "UNF1",
            "name": "Mass",
            "type": "Convertible",
            "siUnit": "kg",
            "dimension": "Mass",
            "status": "active",
            "origin": "Albert Managed",
            "created": _AUDIT,
        }
    )
    assert search_item.si_unit == "kg"
    assert not hasattr(search_item, "units")

    lookup = UnitFamilyV4Lookup.model_validate(
        {"exists": True, "similarMatches": [{"id": "UNF1", "name": "Mass"}]}
    )
    assert lookup.exists is True
    assert lookup.similar_matches[0].id == "UNF1"


def test_unit_family_v4_create_payload_omits_read_only_fields():
    """A convertible family create body carries only the caller-supplied fields."""
    family = UnitFamilyV4(
        name="Force", type=UnitFamilyV4Type.CONVERTIBLE, unit_expression="kg*m/s^2"
    )
    payload = family.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert payload == {"name": "Force", "type": "Convertible", "unitExpression": "kg*m/s^2"}
