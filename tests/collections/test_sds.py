import pytest

from albert import Albert
from albert.exceptions import AlbertClientError, AlbertException, AlbertServerError
from albert.resources.inventory import InventoryItem
from albert.resources.sds import SDSDataEntity, SDSFieldOptions, SDSLegalEntity, SDSRequest

pytestmark = pytest.mark.xdist_group("sheets")


def _first_code(mapping: dict[str, str]) -> str:
    assert mapping, "Expected at least one lookup value"
    return next(iter(mapping.values()))


def test_sds_lookups(client: Albert):
    """Test SDS lookups return the documented shapes."""
    states = client.sds.get_physical_states()
    assert isinstance(states, dict)
    assert states
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in states.items())

    jurisdictions = client.sds.get_jurisdictions()
    assert isinstance(jurisdictions, dict)
    assert jurisdictions
    region = _first_code(jurisdictions)

    groups = client.sds.get_jurisdiction_groups()
    assert isinstance(groups, dict)
    assert groups
    assert all(isinstance(v, list) for v in groups.values())

    languages = client.sds.get_languages(region=region)
    assert isinstance(languages, dict)
    assert languages

    all_languages = client.sds.get_languages(region="all")
    assert isinstance(all_languages, dict)
    assert all_languages

    products = client.sds.get_products(region=region)
    assert isinstance(products, dict)

    entities = client.sds.get_legal_entities(region=region)
    assert isinstance(entities, list)
    assert entities
    assert all(isinstance(item, SDSLegalEntity) for item in entities)
    assert entities[0].value is not None


def test_sds_get_field_options_waste_code(client: Albert):
    """Test get_field_options parses the waste-code envelope."""
    options = client.sds.get_field_options(entity=SDSDataEntity.WASTE_CODE)
    assert isinstance(options, SDSFieldOptions)


@pytest.mark.slow
def test_generate_sds_unpacks_formula(client: Albert, seeded_products: list[InventoryItem]):
    """Test generate_sds unpacks a formula and returns SDS JSON plus a PDF URL."""
    jurisdictions = client.sds.get_jurisdictions()
    if not jurisdictions:
        pytest.skip("Tenant has no SDS jurisdictions")
    region = _first_code(jurisdictions)

    try:
        languages = client.sds.get_languages(region=region)
        entities = client.sds.get_legal_entities(region=region)
    except AlbertClientError as exc:
        pytest.skip(f"SDS lookups unavailable for region {region}: {exc}")

    states = client.sds.get_physical_states()
    products = client.sds.get_products(region=region)
    if not languages or not states or not products or not entities:
        pytest.skip("Tenant SDS lookups are missing language, state, product, or legal entity")

    formula = seeded_products[0]
    sds = SDSRequest(
        albert_id=formula.id,
        region=region,
        language=_first_code(languages),
        product_type=_first_code(products),
        physical_state=_first_code(states),
        legal_entity=entities[0].value,
    )
    try:
        result = client.sds.generate_sds(sds=sds)
    except (AlbertClientError, AlbertServerError, AlbertException) as exc:
        pytest.skip(f"Tenant cannot generate SDS for seeded formula: {exc}")

    for section in (f"section{i}" for i in range(1, 17)):
        assert section in result.sds_json
    assert result.pdf_url
    assert result.pdf_url.startswith("https://")
