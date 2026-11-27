import json

import responses

from albert.collections.data_templates import DataTemplateCollection
from albert.resources.data_templates import DataColumnValue, DataTemplate
from albert.utils._patch import _data_column_hidden_patch, generate_data_column_patches
from tests.unit.conftest import UNIT_BASE_URL

DT_URL = f"{UNIT_BASE_URL}/api/v3/datatemplates"


def _dc(**kwargs) -> DataColumnValue:
    kwargs.setdefault("data_column_id", "DAC1")
    kwargs.setdefault("sequence", "1")
    return DataColumnValue(**kwargs)


def _returned_columns(count: int, *, with_default: bool = False) -> list[dict]:
    cols = [
        {"id": f"DAC{i}", "name": f"Col {i}", "sequence": f"COL{i}", "hidden": False}
        for i in range(1, count + 1)
    ]
    if with_default:
        cols.append({"id": "DAC456", "name": "Default", "sequence": "COL0", "hidden": False})
    return cols


def _patch_bodies() -> list[dict]:
    return [json.loads(c.request.body) for c in responses.calls if c.request.method == "PATCH"]


def test_hidden_patch_matrix():
    assert _data_column_hidden_patch(_dc(hidden=False), _dc(hidden=False)) is None
    assert _data_column_hidden_patch(_dc(hidden=True), _dc(hidden=True)) is None
    patch = _data_column_hidden_patch(_dc(hidden=False), _dc(hidden=True))
    assert patch.model_dump(mode="json", by_alias=True, exclude_none=True) == {
        "operation": "update",
        "attribute": "hidden",
        "oldValue": False,
        "newValue": True,
    }


def test_update_patches_include_hidden_change():
    patches, _, _ = generate_data_column_patches(
        initial_data_column=[_dc(hidden=False)], updated_data_column=[_dc(hidden=True)]
    )
    dumped = [p.model_dump(mode="json", by_alias=True, exclude_none=True) for p in patches]
    assert dumped == [
        {
            "attribute": "datacolumn",
            "colId": "1",
            "actions": [
                {"operation": "update", "attribute": "hidden", "oldValue": False, "newValue": True}
            ],
        }
    ]


@responses.activate
def test_create_applies_hidden_after_post(offline_session):
    responses.post(
        DT_URL,
        json={
            "albertId": "DAT1",
            "name": "T",
            "DataColumns": _returned_columns(2, with_default=True),
        },
    )
    responses.patch(f"{DT_URL}/DAT1", status=204)
    responses.get(f"{DT_URL}/DAT1", json={"albertId": "DAT1", "name": "T"})

    DataTemplateCollection(session=offline_session).create(
        data_template=DataTemplate(
            name="T",
            data_column_values=[
                DataColumnValue(data_column_id="DAC1"),
                DataColumnValue(data_column_id="DAC2", hidden=True),
            ],
        )
    )

    assert _patch_bodies() == [
        {
            "data": [
                {
                    "attribute": "datacolumn",
                    "colId": "COL2",
                    "actions": [
                        {
                            "operation": "update",
                            "attribute": "hidden",
                            "oldValue": False,
                            "newValue": True,
                        }
                    ],
                }
            ]
        }
    ]


@responses.activate
def test_create_without_hidden_sends_no_patch(offline_session):
    responses.post(
        DT_URL,
        json={
            "albertId": "DAT1",
            "name": "T",
            "DataColumns": _returned_columns(1, with_default=True),
        },
    )

    DataTemplateCollection(session=offline_session).create(
        data_template=DataTemplate(
            name="T", data_column_values=[DataColumnValue(data_column_id="DAC1")]
        )
    )

    assert _patch_bodies() == []


@responses.activate
def test_add_data_columns_applies_hidden_even_when_echoed(offline_session):
    echoed = _returned_columns(1)
    echoed[0]["hidden"] = True
    responses.put(f"{DT_URL}/DAT1/datacolumns", json={"DataColumns": echoed})
    responses.patch(f"{DT_URL}/DAT1", status=204)
    responses.get(f"{DT_URL}/DAT1", json={"albertId": "DAT1", "name": "T"})

    DataTemplateCollection(session=offline_session).add_data_columns(
        data_template_id="DAT1",
        data_columns=[DataColumnValue(data_column_id="DAC1", hidden=True)],
    )

    bodies = _patch_bodies()
    assert len(bodies) == 1
    assert bodies[0]["data"][0]["colId"] == "COL1"
    assert bodies[0]["data"][0]["actions"][0]["newValue"] is True
