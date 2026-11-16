from albert.collections.descriptors import _calculate_payload
from albert.resources.descriptors import DescriptorFamily


def test_calculate_payload_omits_config_when_no_selection() -> None:
    """No names and no families leaves the service on its default descriptor set."""
    assert _calculate_payload(smiles=["CCO"], names=None, families=None) == {"smiles": ["CCO"]}


def test_calculate_payload_sends_names_and_family_values() -> None:
    """Names and families are combined, and a family is sent as its wire value."""
    payload = _calculate_payload(
        smiles=["CCO"],
        names=["MolecularWeight"],
        families=[DescriptorFamily.COMPOSITION],
    )
    assert payload == {
        "smiles": ["CCO"],
        "config": {"names": ["MolecularWeight"], "families": ["composition"]},
    }


def test_calculate_payload_keeps_an_explicit_empty_selection() -> None:
    """An empty list is the caller's selection, so it is sent rather than omitted."""
    payload = _calculate_payload(smiles=["CCO"], names=[], families=None)
    assert payload["config"] == {"names": []}
