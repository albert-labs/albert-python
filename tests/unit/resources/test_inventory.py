import pytest
from pydantic import ValidationError

from albert.core.shared.models.base import EntityLink
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.inventory import (
    CasAmount,
    InventoryCategory,
    InventoryDensity,
    InventoryItem,
    InventoryMinimum,
    InventorySpecValue,
    InventoryUnitCategory,
)
from albert.resources.locations import Location


def test_cas_amount_attributes():
    cas = Cas(number="test", smiles="CCC", id="dogs")
    amt = CasAmount(min=5, max=95, cas=cas)

    assert amt.cas is cas
    assert amt.id == "dogs"
    assert amt.number == "test"
    assert amt.cas_smiles == "CCC"

    data = amt.model_dump(exclude_none=True)
    assert set(data.keys()) == {"min", "max", "id"}

    full = amt.model_dump(exclude_none=False)
    assert set(full.keys()) == {
        "min",
        "max",
        "target",
        "id",
        "cas_category",
        "inventory_function",
        "created",
        "updated",
        "classification_type",
        "type",
        "substance_id",
    }


def test_formula_requirements():
    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test",
            description="Test",
            category=InventoryCategory.FORMULAS,
        )


def test_inventory_metadata_preserves_named_links_and_supports_id_only_links():
    item = InventoryItem(
        name="Test",
        category=InventoryCategory.RAW_MATERIALS,
        metadata={
            "named": [{"id": "LST1", "name": "United States"}],
            "id_only": [EntityLink(id="LST2")],
        },
    )

    assert item.metadata["named"][0].name == "United States"
    assert item.model_dump(mode="json", by_alias=True)["Metadata"] == {
        "named": [{"id": "LST1", "name": "United States"}],
        "id_only": [{"id": "LST2"}],
    }


def test_inventory_volume_density_coercion_and_serialization():
    item = InventoryItem(
        name="Test Volume Item",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.VOLUME,
        density=0.785,
    )
    assert isinstance(item.density, InventoryDensity)
    assert item.density.value == 0.785

    dumped = item.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["density"] == 0.785
    assert isinstance(dumped["density"], (int, float))


def test_inventory_density_object_passes_through_coercion():
    """Test that an existing InventoryDensity object is not re-wrapped by the coercion validator."""
    density = InventoryDensity(value=0.5)
    item = InventoryItem(
        name="Test Volume Item",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.VOLUME,
        density=density,
    )

    assert item.density is density


def test_inventory_volume_density_validation():
    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
        )

    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
            density=0,
        )

    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
            density=-0.5,
        )


def test_inventory_volume_get_deserialization_without_density():
    item = InventoryItem(
        name="Existing Volume Item",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.VOLUME,
        albertId="INVA12345",
    )
    assert item.id == "INVA12345"
    assert item.density is None


def test_cas_amount_without_cas_object_keeps_explicit_id():
    """Test that CasAmount accepts a bare id without a cas object and leaves derived fields unset."""
    amt = CasAmount(min=5, max=95, id="CAS9999999")

    assert amt.cas is None
    assert amt.id == "CAS9999999"
    assert amt.number is None
    assert amt.cas_smiles is None


def test_inventory_minimum_requires_id_or_location():
    """Test that InventoryMinimum raises when neither id nor location is provided."""
    with pytest.raises(ValidationError):
        InventoryMinimum(minimum=5)


def test_inventory_minimum_with_id_only_skips_location_derivation():
    """Test that InventoryMinimum accepts a bare id with no location object."""
    minimum = InventoryMinimum(id="LOC1", minimum=5)

    assert minimum.id == "LOC1"
    assert minimum.location is None


def test_inventory_minimum_rejects_mismatched_id_and_location():
    """Test that InventoryMinimum raises when id and location.id disagree."""
    location = Location(
        name="Boston Lab", albertId="LOC1", latitude=1.0, longitude=2.0, address="x"
    )

    with pytest.raises(ValidationError):
        InventoryMinimum(id="LOC2", location=location, minimum=5)


def test_inventory_minimum_from_location_sets_id():
    """Test that InventoryMinimum derives id from a location object and excludes location from the dump."""
    location = Location(
        name="Boston Lab", albertId="LOC1", latitude=1.0, longitude=2.0, address="x"
    )

    minimum = InventoryMinimum(location=location, minimum=5)

    assert minimum.id == "LOC1"
    assert minimum.model_dump(by_alias=True, exclude_none=True) == {"id": "LOC1", "minimum": 5.0}


def test_inventory_minimum_matching_id_and_location_is_accepted():
    """Test that InventoryMinimum accepts an id and location that agree."""
    location = Location(
        name="Boston Lab", albertId="LOC1", latitude=1.0, longitude=2.0, address="x"
    )

    minimum = InventoryMinimum(id="LOC1", location=location, minimum=5)

    assert minimum.id == "LOC1"


def test_inventory_company_string_is_coerced_to_company():
    """Test that a bare company name string is coerced into a Company object."""
    item = InventoryItem(name="Test", category=InventoryCategory.RAW_MATERIALS, company="Acme")

    assert isinstance(item.company, Company)
    assert item.company.name == "Acme"


def test_inventory_company_object_passes_through():
    """Test that an existing Company object is kept as-is."""
    company = Company(name="Acme Direct")
    item = InventoryItem(name="Test", category=InventoryCategory.RAW_MATERIALS, company=company)

    assert item.company is company


@pytest.mark.parametrize(
    ("un_number", "expected"),
    [
        ("N/A", None),
        ("UN1234", "UN1234"),
        (None, None),
    ],
)
def test_inventory_un_number_treats_na_as_none(un_number, expected):
    """Test that an un_number of 'N/A' is coerced to None while other values pass through."""
    item = InventoryItem(name="Test", category=InventoryCategory.RAW_MATERIALS, unNumber=un_number)

    assert item.un_number == expected


@pytest.mark.parametrize(
    ("category", "extra", "expected_unit_category"),
    [
        (InventoryCategory.RAW_MATERIALS, {}, InventoryUnitCategory.MASS),
        (InventoryCategory.CONSUMABLES, {}, InventoryUnitCategory.UNITS),
        (InventoryCategory.EQUIPMENT, {}, InventoryUnitCategory.UNITS),
        (InventoryCategory.FORMULAS, {"project_id": "PRO1"}, InventoryUnitCategory.MASS),
    ],
)
def test_inventory_unit_category_defaults_from_category(category, extra, expected_unit_category):
    """Test that unit_category defaults from category when the caller does not set it."""
    item = InventoryItem(name="Test", category=category, **extra)

    assert item.unit_category == expected_unit_category


def test_inventory_unit_category_explicit_value_is_kept():
    """Test that an explicitly supplied unit_category is not overridden by the category default."""
    item = InventoryItem(
        name="Test",
        category=InventoryCategory.CONSUMABLES,
        unit_category=InventoryUnitCategory.LENGTH,
    )

    assert item.unit_category == InventoryUnitCategory.LENGTH


def test_inventory_formula_with_project_id_is_accepted():
    """Test that a Formula item with a project_id does not raise."""
    item = InventoryItem(name="Test", category=InventoryCategory.FORMULAS, project_id="PRO1")

    assert item.project_id == "PRO1"


def test_inventory_formula_with_existing_id_is_accepted_without_project_id():
    """Test that a legacy Formula item already on the platform (has an id) skips the project_id requirement."""
    item = InventoryItem(name="Test", category=InventoryCategory.FORMULAS, albertId="INVA9999999")

    assert item.id == "INVA9999999"
    assert item.project_id is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1"),
        (2.5, "2.5"),
        ("already", "already"),
        (None, None),
    ],
)
def test_inventory_spec_value_casts_numeric_fields_to_str(value, expected):
    """Test that InventorySpecValue coerces numeric min/max/reference values to strings."""
    spec_value = InventorySpecValue(min=value, max=value, reference=value)

    assert spec_value.min == expected
    assert spec_value.max == expected
    assert spec_value.reference == expected
