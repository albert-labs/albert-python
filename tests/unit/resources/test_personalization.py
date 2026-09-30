"""Unit tests for the Personalization resource model's wire round-trips."""

from albert.resources.personalization import Personalization, PersonalizationCategory


def test_personalization_reads_albert_id_from_list_payload() -> None:
    """Test that a list response keyed by ``albertId`` populates ``id``."""
    record = Personalization(
        **{
            "albertId": "USP27",
            "category": "Starred Projects",
            "parentId": "USR4227",
            "savedId": "PROMO130903",
            "savedName": "test-worksheets",
            "status": "active",
        }
    )

    assert record.id == "USP27"
    assert record.category is PersonalizationCategory.STARRED_PROJECTS
    assert record.saved_id == "PROMO130903"


def test_personalization_reads_id_from_create_payload() -> None:
    """Test that a create response keyed by ``id`` populates ``id``."""
    record = Personalization(
        **{
            "id": "USP17620",
            "parentId": "USR4227",
            "savedId": "PROMO130903",
            "category": "Starred Projects",
        }
    )

    assert record.id == "USP17620"


def test_personalization_create_dump_uses_wire_aliases() -> None:
    """Test that a caller-built record dumps to the wire create shape."""
    record = Personalization(
        category=PersonalizationCategory.STARRED_PROJECTS,
        saved_id="PRO123",
        saved_name="Weatherproof Coatings 2026",
    )

    payload = record.model_dump(by_alias=True, exclude_none=True, exclude_unset=True, mode="json")

    assert payload == {
        "category": "Starred Projects",
        "savedId": "PRO123",
        "savedName": "Weatherproof Coatings 2026",
    }
