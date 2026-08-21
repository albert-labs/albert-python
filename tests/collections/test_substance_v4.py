import uuid

import pytest

from albert.client import Albert
from albert.resources.custom_fields import CustomField, FieldType, ServiceType
from albert.resources.substance_v4 import (
    SubstanceV4Attribute,
    SubstanceV4Create,
    SubstanceV4Identifier,
    SubstanceV4Info,
    SubstanceV4Response,
    SubstanceV4SearchItem,
)

pytestmark = pytest.mark.xdist_group("projects")

CAS_IDS = [
    "134180-76-0",
    "26530-20-1",
    "68515-48-0",
    "1330-20-7",
    "7732-18-5",
]

WATER_CAS = "7732-18-5"


def _search_item_key(
    item: SubstanceV4SearchItem,
) -> tuple[str | None, str | None, str | None]:
    return (item.substance_id, item.cas_id, item.classification_type)


def test_get_by_ids(client: Albert):
    """Test retrieving multiple substances by CAS IDs."""
    response = client.substances_v4.get_by_ids(cas_ids=CAS_IDS)
    assert isinstance(response, SubstanceV4Response)
    assert len(response.substances) >= len(
        CAS_IDS
    )  # API may return multiple entries per CAS (e.g. different classification types)
    for substance in response.substances:
        assert isinstance(substance, SubstanceV4Info)


def test_get_by_id(client: Albert):
    """Test retrieving a single substance by CAS ID."""
    substance = client.substances_v4.get_by_id(cas_id="7732-18-5")
    assert substance is not None
    assert isinstance(substance, SubstanceV4Info)
    assert substance.cas_id == "7732-18-5"


def test_get_by_id_not_found(client: Albert):
    """Test that get_by_id returns None for a non-existent CAS ID."""
    substance = client.substances_v4.get_by_id(cas_id="DUMMY-CAS-NO")
    assert substance is None


def test_get_by_id_region(client: Albert):
    """Test retrieving a substance with a specific region."""
    substance = client.substances_v4.get_by_id(cas_id="134180-76-0", region="EU")
    assert substance is not None
    assert substance.cas_id == "134180-76-0"


def test_get_by_ids_requires_at_least_one_identifier(client: Albert):
    """Test that get_by_ids raises when no identifier is provided."""
    with pytest.raises(ValueError):
        client.substances_v4.get_by_ids()


def test_update_metadata(client: Albert, static_custom_fields: list[CustomField]):
    """Test updating scalar and custom string metadata fields on a tenant substance."""
    substance_string_field = next(
        cf
        for cf in static_custom_fields
        if cf.service == ServiceType.SUBSTANCES and cf.field_type == FieldType.STRING
    )

    # Create a fresh tenant substance each run (unique ts → always new, no oldValue mismatch)
    result = client.substances_v4.create(
        substance=SubstanceV4Create(
            is_global_record=False,
            identifiers=[
                SubstanceV4Identifier(
                    attributeName="ts", value=f"sdk-test-sub-{uuid.uuid4().hex[:8]}"
                )
            ],
            attributes=[
                SubstanceV4Attribute(
                    attributeName="name",
                    region="global",
                    data=[{"name": "SDK Test Substance", "language_code": "EN"}],
                ),
            ],
        )
    )
    assert result.created_items, "Expected a freshly created substance"
    sub_id = result.created_items[0].substance_id
    assert sub_id

    client.substances_v4.update_metadata(
        id=sub_id,
        notes="sdk test note",
        cas_smiles="CCO",
        metadata={substance_string_field.name: "sdk test value"},
    )


def test_search_requires_at_least_one_filter(client: Albert):
    """Test that search raises when no filter is provided."""
    with pytest.raises(ValueError):
        list(client.substances_v4.search())


def test_search_filters(client: Albert):
    """Test search_key, cas, and name filters return expected records."""
    by_key = list(client.substances_v4.search(search_key=WATER_CAS, max_items=20))
    assert by_key
    assert all(isinstance(r, SubstanceV4SearchItem) for r in by_key)
    assert any(r.cas_id == WATER_CAS for r in by_key)

    by_cas = list(client.substances_v4.search(cas=WATER_CAS, max_items=20))
    assert by_cas
    assert all(r.cas_id == WATER_CAS for r in by_cas)

    by_name = list(client.substances_v4.search(name="water", max_items=20))
    assert by_name
    assert all(isinstance(r, SubstanceV4SearchItem) for r in by_name)
    assert any(r.cas_id == WATER_CAS for r in by_name)


def test_search_pagination(client: Albert):
    """Test max_items cap, start_key resume, multi-page uniqueness, and has_more."""
    capped_pag = client.substances_v4.search(search_key="water", max_items=5)
    capped = list(capped_pag)
    assert len(capped) == 5
    assert capped_pag.has_more is True
    assert capped_pag.total is not None
    assert capped_pag.total > len(capped)

    results = list(client.substances_v4.search(search_key="water", max_items=45))
    keys = [_search_item_key(r) for r in results]
    assert len(keys) == len(set(keys))

    if len(results) >= 20:
        first_page_keys = {_search_item_key(r) for r in results[:20]}
        resumed = list(client.substances_v4.search(search_key="water", start_key=20, max_items=20))
        assert resumed
        assert not first_page_keys & {_search_item_key(r) for r in resumed}
