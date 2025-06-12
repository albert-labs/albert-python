from albert.resources.lists import ListItem
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.tasks import BaseTask
from albert.utils.patch_types import PatchDatum, PatchOperation, PatchPayload


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
