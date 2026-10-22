"""Unit tests for the Localization resource models' wire round-trips."""

import pytest
from pydantic import ValidationError

from albert.resources.localizations import (
    Localization,
    LocalizationLanguage,
    LocalizationPatchDatum,
    LocalizationValidation,
)

# Recorded from the api-localization OpenAPI spec examples ("Localizations with DAC and PRM").
LOCALIZATION_ROWS = [
    {
        "albertId": "DAT1",
        "name": "Data Template",
        "uniqueId": "DAT",
        "description": "Data Template description",
        "localization": {"name": {"de": "Datenvorlage"}},
        "type": "string",
        "module": "DAT",
    },
    {
        "albertId": "DAT1",
        "uniqueId": "DAC1#COL0",
        "name": "Comments",
        "localization": {"name": {"de": "Kommentre"}},
        "type": "string",
        "hidden": True,
        "module": "DAC",
    },
    {
        "albertId": "DAT1",
        "uniqueId": "PRM1#ROW1",
        "name": "time",
        "localization": {"name": {"de": "Zeit"}},
        "type": "string",
        "hidden": True,
        "module": "PRM",
    },
]


def test_localization_reads_wire_fields() -> None:
    """Test that wire aliases populate the model fields."""
    row = Localization(**LOCALIZATION_ROWS[0])

    assert row.id == "DAT1"
    assert row.unique_id == "DAT"
    assert row.localization == {"name": {"de": "Datenvorlage"}}


def test_localization_round_trips_child_records() -> None:
    """Test that parent and child rows parse into the same model."""
    rows = [Localization(**item) for item in LOCALIZATION_ROWS]

    assert [row.unique_id for row in rows] == ["DAT", "DAC1#COL0", "PRM1#ROW1"]
    assert rows[1].hidden is True
    assert rows[2].module == "PRM"


def test_localization_reads_enum_validation_translations() -> None:
    """Test that enum option translations survive validation parsing."""
    row = Localization(
        **{
            "albertId": "DAT1",
            "uniqueId": "DAC1#COL2",
            "name": "Fruits",
            "validation": [
                {
                    "datatype": "enum",
                    "value": [
                        {
                            "id": "ENM1",
                            "text": "Apple",
                            "localization": {"text": {"de": "Apfel"}},
                        },
                        {
                            "id": "ENM2",
                            "text": "Banana",
                            "localization": {"text": {"de": "Banane"}},
                        },
                    ],
                }
            ],
            "type": "enum",
            "module": "DAC",
        }
    )

    rule = row.validation[0]
    assert rule.datatype == "enum"
    assert rule.value[0].localization == {"text": {"de": "Apfel"}}
    assert rule.value[1].text == "Banana"


def test_localization_reads_scalar_validation() -> None:
    """Test that a numeric bound rule parses alongside enum rules."""
    row = Localization(
        **{
            "albertId": "DAT1",
            "uniqueId": "DAC1#COL3",
            "name": "Fruits",
            "validation": [{"datatype": "number", "value": 20, "operator": "lt"}],
            "type": "number",
            "module": "DAC",
        }
    )

    rule = row.validation[0]
    assert isinstance(rule, LocalizationValidation)
    assert rule.value == 20
    assert rule.operator == "lt"


def test_localization_tolerates_row_without_translations() -> None:
    """Test that a row with no ``localization`` key parses with None translations.

    Recorded live: GET /api/v3/localizations/DAC1031 returns rows without
    ``localization``, ``hidden``, or ``required`` when nothing is translated.
    """
    row = Localization(
        **{
            "albertId": "DAC1031",
            "uniqueId": "DAC",
            "name": "Efficiency Cleaning",
            "type": "string",
            "module": "DAC",
        }
    )

    assert row.localization is None
    assert row.hidden is None


def test_localization_tolerates_row_without_unique_id() -> None:
    """Test that a main-entity row missing ``uniqueId`` still parses."""
    row = Localization(
        **{
            "albertId": "DAT1",
            "name": "Data Template",
            "localization": {"name": {"de": "Datenvorlage"}},
            "type": "string",
            "module": "DAT",
        }
    )

    assert row.unique_id is None


def test_localization_patch_datum_serializes_wire_format() -> None:
    """Test that a patch datum serializes to the wire format."""
    datum = LocalizationPatchDatum(
        operation="add",
        attribute="name",
        language="de",
        unique_id="DAC1#ROW1",
        new_value="Kommentre",
    )

    assert datum.model_dump(by_alias=True, exclude_unset=True, mode="json") == {
        "operation": "add",
        "attribute": "name",
        "language": "de",
        "uniqueId": "DAC1#ROW1",
        "newValue": "Kommentre",
    }


def test_localization_patch_datum_omits_unset_values() -> None:
    """Test that an unset ``old_value`` is omitted, e.g. for add operations."""
    datum = LocalizationPatchDatum(
        operation="delete",
        attribute="name",
        language="de",
        unique_id="DAT",
        old_value="Neue Datenvorlage",
    )

    dumped = datum.model_dump(by_alias=True, exclude_unset=True, mode="json")
    assert "oldValue" in dumped
    assert "newValue" not in dumped


@pytest.mark.parametrize("field", ["language", "unique_id"])
def test_localization_patch_datum_requires_language_and_unique_id(field: str) -> None:
    """Test that the required fields reject omission."""
    kwargs = {
        "operation": "add",
        "attribute": "name",
        "language": "de",
        "unique_id": "DAT",
        "new_value": "Datenvorlage",
    }
    del kwargs[field]

    with pytest.raises(ValidationError):
        LocalizationPatchDatum(**kwargs)


def test_localization_language_serializes_to_language_code() -> None:
    """Test that enum members serialize to their language code."""
    datum = LocalizationPatchDatum(
        operation="add",
        attribute="name",
        language=LocalizationLanguage.GERMAN,
        unique_id="DAT",
        new_value="Datenvorlage",
    )

    assert datum.language is LocalizationLanguage.GERMAN
    assert datum.model_dump(by_alias=True, exclude_unset=True, mode="json")["language"] == "de"


def test_localization_patch_datum_accepts_language_codes_not_in_enum() -> None:
    """Test that a plain language code stays usable for languages the enum does not cover yet."""
    datum = LocalizationPatchDatum(
        operation="add",
        attribute="name",
        language="fr",
        unique_id="DAT",
        new_value="Modèle de données",
    )

    assert datum.language == "fr"
