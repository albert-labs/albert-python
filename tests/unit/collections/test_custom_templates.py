"""Unit tests for the pure helpers on CustomTemplatesCollection."""

from albert.collections.custom_templates import CustomTemplatesCollection
from albert.resources.custom_templates import (
    Block,
    CustomTemplate,
    GeneralData,
    Priority,
    PropertyData,
    TemplateCategory,
    Workflow,
    WorkflowCombination,
)
from albert.resources.interval_combinations import (
    CombinationOverride,
    ExclusionRule,
    OverrideAction,
    RuleCondition,
    RuleOperator,
)
from albert.resources.tags import Tag


def _template(**kwargs) -> CustomTemplate:
    defaults = {"name": "tpl"}
    defaults.update(kwargs)
    return CustomTemplate(**defaults)


def _grid() -> list[WorkflowCombination]:
    """Build a 2 x 3 interval-combination grid, all cells enabled."""
    return [
        WorkflowCombination(
            index=index,
            interval_params=f"INT{value1}XINT{value2}",
            heading="Temperature",
            val=str(value1),
            unit_name="C",
            heading2="Stir Rate",
            val2=str(value2),
            unit_name2="RPM",
            is_checked=True,
        )
        for index, (value1, value2) in enumerate([(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)])
    ]


def _property_template(**kwargs) -> CustomTemplate:
    data = PropertyData(
        name="tpl",
        priority=Priority.LOW,
        blocks=[Block(workflow=[Workflow(id="WFL1", combination=_grid())])],
    )
    return _template(
        id="CTP1",
        category=TemplateCategory.PROPERTY,
        data=data,
        **kwargs,
    )


def test_fold_tags_into_data_appends_top_level_after_data_tags() -> None:
    """Test that top-level tags are appended after existing data tags and cleared."""
    template = _template(
        tags=[Tag(id="TAG1", tag="alpha")],
        data=GeneralData(name="tpl", tags=[Tag(id="TAG2", tag="beta")]),
    )

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG2", "TAG1"]
    assert template.tags is None


def test_fold_tags_into_data_sets_data_tags_when_only_top_level() -> None:
    """Test that top-level tags move into a data section that has none."""
    template = _template(tags=[Tag(id="TAG1", tag="alpha")], data=GeneralData(name="tpl"))

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG1"]
    assert template.tags is None


def test_fold_tags_into_data_noops_without_top_level_tags() -> None:
    """Test that data tags are untouched when no top-level tags are set."""
    template = _template(data=GeneralData(name="tpl", tags=[Tag(id="TAG2", tag="beta")]))

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG2"]


def test_fold_tags_into_data_noops_without_data_section() -> None:
    """Test that a template without a data section keeps its top-level tags."""
    template = _template(tags=[Tag(id="TAG1", tag="alpha")])

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.tags] == ["TAG1"]


def test_patch_empty_when_no_set_field_differs() -> None:
    """Test that no patch operations are generated when nothing set differs."""
    existing = _property_template()
    updated = _template(id="CTP1", name="tpl", category=TemplateCategory.PROPERTY)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert operations == []


def test_patch_data_unset_leaves_data_untouched() -> None:
    """Test that an unset data section produces no Data operation even when set on the server."""
    existing = _property_template()
    updated = _template(id="CTP1", name="New name", category=TemplateCategory.PROPERTY)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert [op["attribute"] for op in operations] == ["name"]


def test_patch_name_change_emits_name_operation() -> None:
    """Test that a changed name emits a name operation carrying the old value."""
    existing = _property_template()
    updated = _template(id="CTP1", name="New name", category=TemplateCategory.PROPERTY)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert operations == [
        {
            "operation": "update",
            "attribute": "name",
            "oldValue": "tpl",
            "newValue": "New name",
        }
    ]


def test_patch_category_change_emits_enum_values() -> None:
    """Test that a changed category emits a category operation with enum values."""
    existing = _property_template()
    updated = _template(id="CTP1", name="tpl", category=TemplateCategory.GENERAL)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert operations == [
        {
            "operation": "update",
            "attribute": "category",
            "oldValue": "Property",
            "newValue": "General",
        }
    ]


def test_patch_locked_change_emits_operation_without_old_value() -> None:
    """Test that a changed locked flag emits a locked operation without an old value."""
    existing = _property_template()
    updated = _template(id="CTP1", name="tpl", category=TemplateCategory.PROPERTY, locked=True)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert operations == [{"operation": "update", "attribute": "locked", "newValue": True}]


def test_patch_metadata_change_emits_metadata_operation() -> None:
    """Test that a changed metadata emits a Metadata operation carrying both values."""
    existing = _property_template()
    updated = _template(
        id="CTP1",
        name="tpl",
        category=TemplateCategory.PROPERTY,
        metadata={"qcCategory": "WKS"},
    )

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert operations == [
        {
            "operation": "update",
            "attribute": "Metadata",
            "oldValue": None,
            "newValue": {"qcCategory": "WKS"},
        }
    ]


def test_patch_data_cleared_when_explicitly_none() -> None:
    """Test that an explicitly None data section emits a Data operation that clears it."""
    existing = _property_template()
    updated = _template(id="CTP1", name="tpl", category=TemplateCategory.PROPERTY, data=None)

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert [op["attribute"] for op in operations] == ["Data"]
    assert operations[0]["newValue"] == {}


def test_patch_combination_toggle_emits_data_operation() -> None:
    """Test that toggling one combination cell emits a Data operation with both grids."""
    existing = _property_template()
    updated = existing.model_copy(deep=True)
    updated.data.blocks[0].workflow[0].combination[2].is_checked = False

    operations = CustomTemplatesCollection._generate_custom_template_patch(
        existing=existing, updated=updated
    )

    assert [op["attribute"] for op in operations] == ["Data"]
    old_grid = operations[0]["oldValue"]["Blocks"][0]["Workflow"][0]["Combination"]
    new_grid = operations[0]["newValue"]["Blocks"][0]["Workflow"][0]["Combination"]
    assert [cell["isChecked"] for cell in old_grid] == [True] * 6
    assert [cell["isChecked"] for cell in new_grid] == [
        True,
        True,
        False,
        True,
        True,
        True,
    ]


def test_serialize_template_data_uses_wire_keys() -> None:
    """Test that a data section serializes with the documented wire keys."""
    data = PropertyData(
        name="tpl",
        priority=Priority.LOW,
        increased_intervals=True,
        blocks=[
            Block(
                intervals_start_from="none",
                rules=[
                    ExclusionRule(
                        name="Premature crosslinking risk",
                        conditions=[
                            RuleCondition(
                                parameter_group_id="PRG26201",
                                parameter_id="PRM202",
                                row_id="ROW7",
                                name="Temperature",
                                operator=RuleOperator.GT,
                                value=90,
                                unit_id="UNI90",
                            )
                        ],
                    )
                ],
                overrides=[
                    CombinationOverride(
                        key="PRG26201#PRM202#ROW7-PRG26201#PRM1265#ROW12",
                        action=OverrideAction.SKIP,
                        is_manual=True,
                    )
                ],
                workflow=[Workflow(id="WFL1", combination=_grid())],
            )
        ],
    )

    serialized = CustomTemplatesCollection._serialize_template_data(data)

    assert serialized["increasedIntervals"] is True
    block = serialized["Blocks"][0]
    assert block["intervalsStartFrom"] == "none"
    assert block["rules"][0]["name"] == "Premature crosslinking risk"
    condition = block["rules"][0]["conditions"][0]
    assert condition["prgId"] == "PRG26201"
    assert condition["prmId"] == "PRM202"
    assert condition["rowId"] == "ROW7"
    assert condition["operator"] == "gt"
    assert condition["value"] == 90
    assert condition["unitId"] == "UNI90"
    assert block["overrides"][0]["key"] == "PRG26201#PRM202#ROW7-PRG26201#PRM1265#ROW12"
    assert block["overrides"][0]["action"] == "skip"
    assert block["overrides"][0]["isManual"] is True
    assert block["Workflow"][0]["Combination"][0]["intervalParams"] == "INT1XINT1"
    assert block["Workflow"][0]["Combination"][0]["isChecked"] is True


def test_workflow_combination_round_trips_wire_format() -> None:
    """Test that a combination grid round-trips through the wire format unchanged."""
    wire = {
        "category": "Property",
        "name": "tpl",
        "priority": "Low",
        "increasedIntervals": True,
        "Blocks": [
            {
                "intervalsStartFrom": "all",
                "Workflow": [
                    {
                        "id": "WFL1",
                        "Combination": [
                            {
                                "index": 0,
                                "intervalParams": "INT1XINT1",
                                "heading": "Temperature",
                                "val": "25",
                                "unitName": "C",
                                "heading2": "Stir Rate",
                                "val2": "500",
                                "unitName2": "RPM",
                                "isChecked": True,
                                "hidden": False,
                            }
                        ],
                    }
                ],
            }
        ],
    }

    data = PropertyData.model_validate(wire)

    assert CustomTemplatesCollection._serialize_template_data(data) == wire
