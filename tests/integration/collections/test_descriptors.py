import pytest

from albert.client import Albert
from albert.exceptions import BadRequestError
from albert.resources.descriptors import DescriptorFamily, NumericListDescriptorValue


def test_list_descriptor_info_includes_families_and_units(client: Albert) -> None:
    """The catalog returns families, units, and the 3D flag."""
    items = {item.name: item for item in client.descriptors.list_info(all=True)}
    weight = items["MolecularWeight"]
    assert weight.unit == "Da"
    assert "physicochemical" in weight.families
    assert weight.requires_3d is False
    assert items["RadiusOfGyration"].requires_3d is True


def test_list_descriptor_info_defaults_are_a_subset(client: Albert) -> None:
    """all=False returns only the descriptors marked default."""
    defaults = client.descriptors.list_info(all=False)
    assert defaults
    assert all(item.default for item in defaults)
    assert len(defaults) < len(client.descriptors.list_info(all=True))


def test_calculate_descriptors_by_family_returns_units(client: Albert) -> None:
    """A family expands to its descriptors, and each value carries its unit."""
    results = client.descriptors.calculate(smiles=["CCO"], families=[DescriptorFamily.COMPOSITION])
    assert len(results) == 1
    assert results[0].descriptors
    assert all(item.unit == "count" for item in results[0].descriptors)


def test_calculate_named_descriptor_returns_its_unit(client: Albert) -> None:
    """An explicit name is calculated and returned with the catalog unit."""
    results = client.descriptors.calculate(smiles=["CCO"], names=["MolecularWeight"])
    assert len(results[0].descriptors) == 1
    weight = results[0].descriptors[0]
    assert weight.name == "MolecularWeight"
    assert weight.unit == "Da"
    assert isinstance(weight.value.value, float)


def test_calculate_named_fingerprint_returns_numeric_list(client: Albert) -> None:
    """Test that a named fingerprint is returned as a numeric list."""
    results = client.descriptors.calculate(smiles=["CCO"], names=["MACCSKeys"])

    assert len(results) == 1
    fingerprint = results[0].descriptors
    assert len(fingerprint) == 1
    assert fingerprint[0].name == "MACCSKeys"
    assert isinstance(fingerprint[0].value, NumericListDescriptorValue)
    assert isinstance(fingerprint[0].value.value[0], float)


def test_calculate_returns_smiles_in_input_order(client: Albert) -> None:
    """Test that results keep the submitted SMILES in input order."""
    results = client.descriptors.calculate(smiles=["OCC", "NCC"], names=["MolecularWeight"])

    assert [molecule.smiles for molecule in results] == ["OCC", "NCC"]
    assert [molecule.descriptors[0].name for molecule in results] == [
        "MolecularWeight",
        "MolecularWeight",
    ]


def test_calculate_unknown_name_is_rejected(client: Albert) -> None:
    """An unknown descriptor name is a 400 from the service."""
    with pytest.raises(BadRequestError):
        client.descriptors.calculate(smiles=["CCO"], names=["NotADescriptor"])
