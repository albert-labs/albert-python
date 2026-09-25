import pytest
from pydantic import ValidationError

from albert.collections.sds import SDSCollection
from albert.exceptions import AlbertException
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.product_design import UnpackedProductDesign
from albert.resources.sds import SDSRequest


def _identity_kwargs() -> dict:
    return {
        "albert_id": "INVMO1",
        "region": "US",
        "language": "EN",
        "product_type": "acrylate",
        "physical_state": "liquid",
        "legal_entity": 1,
    }


def test_sds_request_requires_region():
    """Test SDSRequest without region fails validation."""
    kwargs = _identity_kwargs()
    kwargs.pop("region")
    with pytest.raises(ValidationError):
        SDSRequest(**kwargs)


def test_sds_request_rejects_composition_lists():
    """Test SDSRequest does not accept caller-supplied composition lists."""
    with pytest.raises(ValidationError):
        SDSRequest(**_identity_kwargs(), substances=[])


def test_sds_request_rejects_name():
    """Test SDSRequest does not accept a caller-supplied product name."""
    with pytest.raises(ValidationError):
        SDSRequest(**_identity_kwargs(), name="MO1")


def test_sds_request_prefixes_inventory_id():
    """Test SDSRequest adds INV when omitted and strips it on dump."""
    kwargs = _identity_kwargs()
    kwargs["albert_id"] = "MO1"
    sds = SDSRequest(**kwargs)
    assert sds.albert_id == "INVMO1"
    payload = sds.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert payload["albertID"] == "MO1"


def test_sds_request_dump_strips_inv_prefix():
    """Test SDSRequest dump uses albertID without a leading INV."""
    sds = SDSRequest(**_identity_kwargs())
    payload = sds.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert payload["albertID"] == "MO1"
    assert "albertId" not in payload
    assert "substances" not in payload
    assert "casLevelSubstances" not in payload
    assert "inventorySDSList" not in payload
    assert "name" not in payload


def test_sds_request_optional_fields_serialize_to_aliases():
    """Test the optional generate fields dump to their exact wire aliases."""
    sds = SDSRequest(
        **_identity_kwargs(),
        intended_use="coatings",
        use="industrial",
        physical_form="liquid",
        waste_code="080410",
        flammability="flammable",
        burning_test_result="positive",
        plm_number="PLM-1",
        ufi_identifier="UFI-1",
        viscosity_input="thin",
        particle_characteristics="fine",
        ph_input="neutral",
        melting_point_range="0-10",
        boiling_point_range="90-110",
        vapor_pressure="low",
        vapor_density="high",
        water_solubility="miscible",
        auto_ignition_temp="300",
        decomposition_temp="250",
        evaporation_rate="slow",
        explosive_limits_lower="1",
        explosive_limits_upper="10",
        odor_threshold="low",
        partition_coefficient="2.5",
    )
    payload = sds.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert payload["intendedUse"] == "coatings"
    assert payload["use"] == "industrial"
    assert payload["physicalForm"] == "liquid"
    assert payload["wasteCode"] == "080410"
    assert payload["flammability"] == "flammable"
    assert payload["burningTestResult"] == "positive"
    assert payload["plmNumber"] == "PLM-1"
    assert payload["ufiIdentifier"] == "UFI-1"
    assert payload["viscosityInput"] == "thin"
    assert payload["particleCharacteristics"] == "fine"
    assert payload["pHInput"] == "neutral"
    assert payload["meltingPointRange"] == "0-10"
    assert payload["boilingPointRange"] == "90-110"
    assert payload["vaporPressure"] == "low"
    assert payload["vaporDensity"] == "high"
    assert payload["waterSolubility"] == "miscible"
    assert payload["autoIgnitionTemp"] == "300"
    assert payload["decompositionTemp"] == "250"
    assert payload["evaporationRate"] == "slow"
    assert payload["explosiveLimitsLower"] == "1"
    assert payload["explosiveLimitsUpper"] == "10"
    assert payload["odorThreshold"] == "low"
    assert payload["partitionCoefficient"] == "2.5"


def test_sds_request_omits_unset_optional_fields():
    """Test unset optional generate fields are excluded from the dump."""
    sds = SDSRequest(**_identity_kwargs())
    payload = sds.model_dump(by_alias=True, mode="json", exclude_none=True)
    for alias in (
        "intendedUse",
        "use",
        "physicalForm",
        "wasteCode",
        "flammability",
        "burningTestResult",
        "plmNumber",
        "ufiIdentifier",
        "viscosityInput",
        "particleCharacteristics",
        "pHInput",
        "meltingPointRange",
        "boilingPointRange",
        "vaporPressure",
        "vaporDensity",
        "waterSolubility",
        "autoIgnitionTemp",
        "decompositionTemp",
        "evaporationRate",
        "explosiveLimitsLower",
        "explosiveLimitsUpper",
        "odorThreshold",
        "partitionCoefficient",
    ):
        assert alias not in payload


def test_sds_request_enforces_backend_max_length():
    """Test fields with a backend maxLength of 100 fail fast client-side."""
    with pytest.raises(ValidationError):
        SDSRequest(**_identity_kwargs(), plm_number="x" * 101)


def test_require_formula_inventory_rejects_raw_materials():
    """Test SDS generate rejects non-formula inventory items."""
    item = InventoryItem(name="ethanol", category=InventoryCategory.RAW_MATERIALS)
    with pytest.raises(AlbertException, match="formula inventory items only"):
        SDSCollection._require_formula_inventory(item)


def test_composition_copies_unpack_substance_rows():
    """Test unpack substances, CAS-level rows, and SDS list are copied through."""
    row = {
        "casPrimaryKeyId": "CAS1",
        "casID": "64-17-5",
        "amount": 0.0034,
        "min": 0.003332,
        "aggregatedFunc": [],
        "target": 0,
        "albertId": "INVB1",
    }
    unpacked = UnpackedProductDesign.model_validate(
        {
            "substances": [row],
            "casLevelSubstances": [row],
            "inventorySDSList": [{"albertId": "INVB1", "class": "N/A", "value": 0}],
        }
    )
    mapped = SDSCollection._composition_from_unpacked(unpacked)
    assert mapped["substances"][0]["casID"] == "64-17-5"
    assert mapped["substances"][0]["min"] == 0.003332
    assert mapped["substances"][0]["albertId"] == "INVB1"
    assert mapped["cas_level_substances"][0]["casPrimaryKeyId"] == "CAS1"
    assert mapped["inventory_sds_list"][0]["class"] == "N/A"
