"""Unit tests for UnitCollection PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_unit_patch_payload`` (synonyms are
diffed as item-level add/delete ops, never a whole-list update) with no I/O
to fake.
"""

from albert.collections.units import UnitCollection
from albert.core.shared.models.patch import PatchOperation
from albert.resources.units import Unit, UnitCategory


def test_unset_synonyms_emits_no_op(offline_session) -> None:
    """Test that synonyms the caller never set produce no patch operation."""
    existing = Unit(id="UNI1", name="gram", symbol="g", synonyms=["g"])
    updated = Unit(id="UNI1", name="gram", symbol="g")  # synonyms unset

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_empty_synonyms_deletes_each_existing_entry(offline_session) -> None:
    """Test that clearing synonyms to [] emits a delete op per existing synonym."""
    existing = Unit(id="UNI1", name="gram", synonyms=["g", "gm"])
    updated = Unit(id="UNI1", name="gram", synonyms=[])

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 2
    assert all(d.attribute == "Synonyms" for d in payload.data)
    assert all(d.operation == PatchOperation.DELETE for d in payload.data)
    assert {d.new_value for d in payload.data} == {"g", "gm"}


def test_added_and_removed_synonyms_emit_item_level_ops(offline_session) -> None:
    """Test that synonym changes emit one add/delete op per changed item, not a list update."""
    existing = Unit(id="UNI1", name="gram", synonyms=["g", "gm"])
    updated = Unit(id="UNI1", name="gram", synonyms=["g", "grams"])

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 2
    add_ops = [d for d in payload.data if d.operation == PatchOperation.ADD]
    delete_ops = [d for d in payload.data if d.operation == PatchOperation.DELETE]
    assert [d.new_value for d in add_ops] == ["grams"]
    assert [d.new_value for d in delete_ops] == ["gm"]
    assert add_ops[0].attribute == "Synonyms"
    assert delete_ops[0].attribute == "Synonyms"


def test_unchanged_synonyms_emit_no_op(offline_session) -> None:
    """Test that identical synonym lists produce no patch operation."""
    existing = Unit(id="UNI1", name="gram", synonyms=["g"])
    updated = Unit(id="UNI1", name="gram", synonyms=["g"])

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_changed_symbol_emits_update(offline_session) -> None:
    """Test that a changed scalar attribute (symbol) still emits an update op."""
    existing = Unit(id="UNI1", name="gram", symbol="g")
    updated = Unit(id="UNI1", name="gram", symbol="gr")

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "symbol"
    assert payload.data[0].operation == PatchOperation.UPDATE
    assert payload.data[0].old_value == "g"
    assert payload.data[0].new_value == "gr"


def test_unset_symbol_emits_no_op(offline_session) -> None:
    """Test that a scalar attribute the caller never set produces no patch operation."""
    existing = Unit(id="UNI1", name="gram", symbol="g", category=UnitCategory.MASS)
    updated = Unit(id="UNI1", name="gram")  # symbol, category unset

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_explicit_none_category_emits_delete(offline_session) -> None:
    """Test that explicitly clearing category to None emits a delete op."""
    existing = Unit(id="UNI1", name="gram", category=UnitCategory.MASS)
    updated = Unit(id="UNI1", name="gram", category=None)

    payload = UnitCollection(session=offline_session)._generate_unit_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].attribute == "category"
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].old_value == UnitCategory.MASS
