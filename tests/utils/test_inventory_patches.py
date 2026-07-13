from albert.resources.inventory import CasAmount
from albert.utils.inventory import _build_cas_patch_operations


def test_cas_patch_ignores_unset_optional_fields():
    """Test CAS patch diff skips optional fields the caller did not set."""
    existing = [
        CasAmount(
            id="CAS1",
            min=0.5,
            max=0.75,
            target=0.6,
            cas_category="Intended",
            substance_id="sub-001",
        )
    ]
    updated = [CasAmount(id="CAS1", min=0.1, max=0.5, target=0.3)]

    operations = _build_cas_patch_operations(existing=existing, updated=updated)

    attributes = {op["attribute"] for op in operations}
    assert attributes == {"min", "max", "inventoryValue"}
    assert "substanceId" not in attributes
    assert "casCategory" not in attributes


def test_cas_patch_includes_explicitly_set_substance_id_on_add():
    """Test substanceId is sent only when explicitly provided on a new CAS entry."""
    updated = [CasAmount(id="CAS2", min=0.2, max=0.8, substance_id="sub-002")]

    operations = _build_cas_patch_operations(existing=[], updated=updated)

    add_operation = next(op for op in operations if op["attribute"] == "casId")
    assert add_operation["substanceId"] == "sub-002"
