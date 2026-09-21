"""Unit tests for the v4 units merge-patch builders.

These helpers are pure (no session), so they can be exercised without the API.
They guard the unset-vs-explicit distinction described in OPINIONS.md.
"""

import pytest

from albert.collections.unit_families_v4 import UnitFamilyV4Collection
from albert.collections.units_v4 import UnitV4Collection
from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type
from albert.resources.units_v4 import UnitFamilyV4Ref, UnitV4, UnitV4Type


def _existing_unit(**overrides) -> UnitV4:
    data = {
        "id": "UNI1",
        "name": "Grams",
        "description": "Grams weight",
        "type": "Convertible",
        "symbol": "g",
        "synonyms": ["g", "grms"],
        "siUnit": "kg",
        "siValue": "0.001",
        "unitFamilies": [{"id": "UNF1", "name": "Mass"}],
    }
    data.update(overrides)
    return UnitV4.model_validate(data)


def test_unit_patch_sends_only_changed_fields():
    """Only fields the caller set and changed are included in the patch."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.description = "Grams, for powders"
    updated.synonyms = ["g", "gram"]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"description": "Grams, for powders", "synonyms": ["g", "gram"]}


def test_unit_patch_leaves_unset_fields_untouched():
    """A partial update object never emits fields the caller did not set."""
    existing = _existing_unit()
    updated = UnitV4(id="UNI1", name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE)

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {}


def test_unit_patch_explicit_none_clears_description():
    """Explicit ``None`` is sent so the server deletes the attribute."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.description = None

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"description": None}


def test_unit_patch_families_on_non_convertible_sends_ids():
    """Non-convertible units may change families; IDs are sent as a plain list."""
    existing = _existing_unit(type="Non-Convertible", siUnit=None, siValue=None)
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF1"), UnitFamilyV4Ref(id="UNF9")]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"unitFamilies": ["UNF1", "UNF9"]}


def test_unit_patch_families_same_set_is_noop():
    """Reordering families without changing membership sends nothing."""
    existing = _existing_unit(
        type="Non-Convertible",
        unitFamilies=[{"id": "UNF1", "name": "A"}, {"id": "UNF2", "name": "B"}],
    )
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF2"), UnitFamilyV4Ref(id="UNF1")]

    patch = UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {}


def test_unit_patch_families_on_convertible_raises():
    """Convertible units derive families from their SI mapping; changing them is an error."""
    existing = _existing_unit()
    updated = existing.model_copy()
    updated.unit_families = [UnitFamilyV4Ref(id="UNF9")]

    with pytest.raises(ValueError, match="non-convertible"):
        UnitV4Collection._generate_merge_patch(existing=existing, updated=updated)


def test_unit_family_patch_sends_only_name_and_description():
    """Only name and description are patchable on a unit family."""
    existing = UnitFamilyV4.model_validate(
        {"id": "UNF1", "name": "Mass", "description": "Old", "type": "Convertible"}
    )
    updated = existing.model_copy()
    updated.name = "Mass (SI)"
    updated.description = "Old"

    patch = UnitFamilyV4Collection._generate_merge_patch(existing=existing, updated=updated)

    assert patch == {"name": "Mass (SI)"}

    untouched = UnitFamilyV4(id="UNF1", name="Mass", type=UnitFamilyV4Type.CONVERTIBLE)
    assert UnitFamilyV4Collection._generate_merge_patch(existing=existing, updated=untouched) == {}
