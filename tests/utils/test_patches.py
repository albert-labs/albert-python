from albert.collections.base import BaseCollection
from albert.collections.companies import CompanyCollection
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.companies import Company
from albert.resources.lists import ListItem
from albert.resources.parameter_groups import ParameterGroup, ParameterValue
from albert.resources.tasks import BaseTask
from albert.utils._patch import generate_parameter_group_patches


def test_exclude_unset_default():
    payload = PatchPayload(
        data=[
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
                old_value=None,
            ),
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
            ),
        ]
    )
    dumped = payload.model_dump(mode="json", by_alias=True)

    datum0 = dumped["data"][0]
    assert datum0["oldValue"] is None
    assert datum0["newValue"] == 4

    datum1 = dumped["data"][1]
    assert "oldValue" not in datum1
    assert datum1["newValue"] == 4


class _DeletableNameCollection(BaseCollection):
    _updatable_attributes = {"name"}


def _company_with_name_cleared() -> Company:
    # ``name`` is required on the model, so bypass validation to build the
    # "explicitly set to None" state an update payload would carry.
    return Company.model_construct(id="COM123", name=None)


def test_delete_op_emitted_by_default() -> None:
    """Test that clearing an updatable attribute emits a delete op by default."""
    existing = Company(id="COM123", name="Acme Chemicals")
    updated = _company_with_name_cleared()

    payload = _DeletableNameCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert len(payload.data) == 1
    assert payload.data[0].operation == PatchOperation.DELETE
    assert payload.data[0].attribute == "name"


def test_non_deletable_attributes_skip_delete_ops() -> None:
    """Test that no delete op is emitted for a non-deletable attribute set to None."""
    existing = Company(id="COM123", name="Acme Chemicals")
    updated = _company_with_name_cleared()

    payload = CompanyCollection(session=None)._generate_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []


def test_parameter_group_row_delete_uses_parameters_attribute():
    """Test that deleting a parameter group row emits the ``parameters`` attribute."""
    existing = ParameterGroup(
        name="Mixing Step",
        parameters=[
            ParameterValue(id="PRM123", value="500", sequence="ROW1"),
            ParameterValue(id="PRM456", value="600", sequence="ROW2"),
        ],
    )
    updated = ParameterGroup(
        name="Mixing Step",
        parameters=[ParameterValue(id="PRM123", value="500", sequence="ROW1")],
    )

    general_patches, _, _ = generate_parameter_group_patches(
        initial_patches=PatchPayload(data=[]),
        updated_parameter_group=updated,
        existing_parameter_group=existing,
    )
    dumped = general_patches.model_dump(mode="json", by_alias=True, exclude_none=True)

    deletes = [d for d in dumped["data"] if d["operation"] == "delete"]
    assert len(deletes) == 1
    assert deletes[0]["attribute"] == "parameters"
    assert deletes[0]["oldValue"] == ["ROW2"]


def change_metadata(
    existing_metadata: dict[str, str | int | list],
    static_lists: list[ListItem],
    seed_prefix: str,
) -> None:
    new_metadata = {}
    for k, v in existing_metadata.items():
        if isinstance(v, str):
            new_str = f"{seed_prefix}-new string"
            new_metadata[k] = new_str
        elif isinstance(v, int):
            new_int = v + 42
            new_metadata[k] = new_int
        elif isinstance(v, list):
            used_ids = [x.id for x in v]
            new_list = [x for x in static_lists if x.id not in used_ids and x.list_type == k]
            new_metadata[k] = [x.to_entity_link() for x in new_list]

    return new_metadata


def make_metadata_update_assertions(
    new_metadata: dict[str, str | int | list], updated_object: ParameterGroup | BaseTask
):
    for key, new_val in new_metadata.items():
        actual_val = updated_object.metadata.get(key)
        assert actual_val is not None, f"Metadata key '{key}' missing in updated group"

        if isinstance(new_val, str):
            assert actual_val == new_val, f"Metadata key '{key}' string mismatch"
        elif isinstance(new_val, int):
            assert actual_val == new_val, f"Metadata key '{key}' int mismatch"
        elif isinstance(new_val, list):
            new_ids = {x.id for x in new_val}
            actual_ids = {x.id for x in actual_val}
            assert new_ids == actual_ids, f"Metadata key '{key}' list mismatch"
