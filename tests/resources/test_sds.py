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
