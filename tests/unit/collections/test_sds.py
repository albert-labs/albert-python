"""How ``get_field_options`` reads the field-options response shapes."""

import responses

from albert.collections.sds import SDSCollection
from tests.unit.conftest import UNIT_BASE_URL

_DATA_URL = f"{UNIT_BASE_URL}/api/v2/documentgenerator/data"


@responses.activate
def test_empty_list_is_not_displayed(offline_session) -> None:
    """Test that a bare empty list is not a field to show.

    That response has no display flag. It is how an unconfigured entity comes back.
    """
    responses.get(f"{_DATA_URL}?entity=viscosityInput", json=[])

    options = SDSCollection(session=offline_session).get_field_options(entity="viscosityInput")

    assert options.display is False
    assert options.data == []


@responses.activate
def test_non_empty_list_is_displayed(offline_session) -> None:
    """Test that a bare option list is a field to show."""
    responses.get(
        f"{_DATA_URL}?entity=wasteCode",
        json=[{"value": "08 01 11", "label": "waste paint"}],
    )

    options = SDSCollection(session=offline_session).get_field_options(entity="wasteCode")

    assert options.display is True
    assert options.data[0]["value"] == "08 01 11"


@responses.activate
def test_explicit_display_true_with_empty_data_stays_displayed(offline_session) -> None:
    """Test that an object with display true is shown even when data is empty."""
    responses.get(
        f"{_DATA_URL}?entity=particleCharacteristics",
        json={"display": True, "isRequired": False, "data": []},
    )

    options = SDSCollection(session=offline_session).get_field_options(
        entity="particleCharacteristics"
    )

    assert options.display is True
    assert options.is_required is False
