"""Verify Pydantic attribute docstrings emit JSON Schema descriptions."""

from albert.resources.data_columns import DataColumn
from albert.resources.inventory import InventoryItem
from albert.resources.projects import Project
from albert.resources.tasks import BaseTask, PropertyTask


def _described_fields(model: type) -> dict[str, str]:
    props = model.model_json_schema().get("properties", {})
    return {k: v["description"] for k, v in props.items() if v.get("description")}


def test_project_fields_have_json_schema_descriptions() -> None:
    described = _described_fields(Project)
    assert "description" in described
    assert "display name" in described["description"].lower()
    assert described.get("Locations", "").startswith("The locations")
    assert described.get("albertId", "").startswith("The Albert Project ID")


def test_data_column_name_description_from_attribute_docstring() -> None:
    described = _described_fields(DataColumn)
    assert described["name"].startswith("The name of the data column")


def test_base_task_core_fields_described() -> None:
    described = _described_fields(BaseTask)
    assert described["name"].startswith("Human-readable")
    assert described.get("parentId", "").startswith("The ID of the parent project")


def test_property_task_inherits_base_task_descriptions() -> None:
    base = _described_fields(BaseTask)
    prop = _described_fields(PropertyTask)
    assert prop.get("name") == base.get("name")


def test_inventory_item_has_field_descriptions() -> None:
    described = _described_fields(InventoryItem)
    assert len(described) >= 10
