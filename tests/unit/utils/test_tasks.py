"""Unit tests for task patch-payload generation and CSV/attachment helpers.

The ``generate_adv_patch_payload`` tests are allowed under the patch-builder
exception in OPINIONS.md: they guard non-obvious diff behavior for the
task-specific special attributes (``assigned_to``, ``inventory_information``,
``tags``, ``project``) with no I/O to fake.
"""

from __future__ import annotations

import types

import pytest
import responses

from albert.collections.tasks import TaskCollection
from albert.core.shared.models.base import EntityLink, EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.resources.attachments import AttachmentMetadata
from albert.resources.data_templates import CurveDataEntityLink, DataColumnValue
from albert.resources.notes import Note, NoteAttachmentEntityLink
from albert.resources.tags import Tag
from albert.resources.tasks import (
    Block,
    GeneralTask,
    PropertyTask,
    TaskInventoryInformation,
)
from albert.utils.tasks import (
    build_property_payload,
    build_task_metadata,
    determine_extension,
    extract_extensions_from_attachment,
    fetch_csv_table_rows,
    generate_adv_patch_payload,
    is_metadata_item_list,
    map_csv_headers_to_columns,
    resolve_attachment,
)
from tests.unit.conftest import UNIT_BASE_URL


def _payload(offline_session, *, existing: GeneralTask, updated: GeneralTask):
    return generate_adv_patch_payload(
        collection=TaskCollection(session=offline_session),
        existing=existing,
        updated=updated,
    )


# ---------------------------------------------------------------------------
# generate_adv_patch_payload -- assigned_to
# ---------------------------------------------------------------------------


def test_assigned_to_unset_emits_no_op(offline_session):
    """Test that an omitted assigned_to on the caller's update object is left untouched."""
    existing = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR1", name="Alice")
    )
    updated = GeneralTask(id="TAS1", name="Task")

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_assigned_to_explicit_none_emits_delete(offline_session):
    """Test that explicitly clearing assigned_to emits a delete op with the old value."""
    existing = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR1", name="Alice")
    )
    updated = GeneralTask(id="TAS1", name="Task", assigned_to=None)

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.DELETE,
            "attribute": "AssignedTo",
            "oldValue": EntityLinkWithName(id="USR1", name="Alice"),
        }
    ]


def test_assigned_to_add_when_previously_unset(offline_session):
    """Test that setting assigned_to when there was none emits an add op."""
    existing = GeneralTask(id="TAS1", name="Task")
    updated = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR2", name="Bob")
    )

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.ADD,
            "attribute": "AssignedTo",
            "newValue": EntityLinkWithName(id="USR2", name="Bob"),
        }
    ]


def test_assigned_to_update_when_id_changes(offline_session):
    """Test that reassigning to a different user emits an update op with a bare-id old value."""
    existing = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR1", name="Alice")
    )
    updated = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR2", name="Bob")
    )

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.UPDATE,
            "attribute": "AssignedTo",
            "oldValue": EntityLink(id="USR1"),
            "newValue": EntityLinkWithName(id="USR2", name="Bob"),
        }
    ]


def test_assigned_to_unchanged_id_with_different_name_is_no_op(offline_session):
    """Test that a name-only difference on the same assignee id emits no op."""
    existing = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR1", name="Alice")
    )
    updated = GeneralTask(
        id="TAS1", name="Task", assigned_to=EntityLinkWithName(id="USR1", name="Alice B.")
    )

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_assigned_to_explicit_none_when_already_unset_is_no_op(offline_session):
    """Test that explicitly setting assigned_to to None when it was already unset is a no-op."""
    existing = GeneralTask(id="TAS1", name="Task")
    updated = GeneralTask(id="TAS1", name="Task", assigned_to=None)

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


# ---------------------------------------------------------------------------
# generate_adv_patch_payload -- inventory_information
# ---------------------------------------------------------------------------


def test_inventory_information_unset_emits_no_op(offline_session):
    """Test that an omitted inventory_information is left untouched."""
    existing = GeneralTask(
        id="TAS1",
        name="Task",
        inventory_information=[TaskInventoryInformation(inventory_id="INV1")],
    )
    updated = GeneralTask(id="TAS1", name="Task")

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_inventory_information_explicit_empty_clears_existing(offline_session):
    """Test that clearing inventory_information to [] deletes every existing entry."""
    existing = GeneralTask(
        id="TAS1",
        name="Task",
        inventory_information=[
            TaskInventoryInformation(inventory_id="INV1", lot_id="LOT1"),
            TaskInventoryInformation(inventory_id="INV2"),
        ],
    )
    updated = GeneralTask(id="TAS1", name="Task", inventory_information=[])

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.DELETE,
            "attribute": "inventory",
            "oldValue": [{"id": "INV1", "lotId": "LOT1"}, {"id": "INV2"}],
        }
    ]


def test_inventory_information_add_and_remove_by_key(offline_session):
    """Test that add/remove are keyed on inventory_id#lot_id, in delete-then-add order."""
    existing = GeneralTask(
        id="TAS1",
        name="Task",
        inventory_information=[
            TaskInventoryInformation(inventory_id="INV1", lot_id="LOT1"),
            TaskInventoryInformation(inventory_id="INV2"),
        ],
    )
    updated = GeneralTask(
        id="TAS1",
        name="Task",
        inventory_information=[
            TaskInventoryInformation(inventory_id="INV2"),
            TaskInventoryInformation(inventory_id="INV3", lot_id="LOT3"),
        ],
    )

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.DELETE,
            "attribute": "inventory",
            "oldValue": [{"id": "INV1", "lotId": "LOT1"}],
        },
        {
            "operation": PatchOperation.ADD,
            "attribute": "inventory",
            "newValue": [{"id": "INV3", "lotId": "LOT3"}],
        },
    ]


def test_inventory_information_unchanged_is_no_op(offline_session):
    """Test that an identical inventory_id/lot_id list emits no operations."""
    items = [TaskInventoryInformation(inventory_id="INV1", lot_id="LOT1")]
    existing = GeneralTask(id="TAS1", name="Task", inventory_information=list(items))
    updated = GeneralTask(id="TAS1", name="Task", inventory_information=list(items))

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


# ---------------------------------------------------------------------------
# generate_adv_patch_payload -- tags
# ---------------------------------------------------------------------------


def test_tags_unset_emits_no_op(offline_session):
    """Test that an omitted tags list is left untouched."""
    existing = GeneralTask(id="TAS1", name="Task", tags=[Tag(id="TAG1", tag="A")])
    updated = GeneralTask(id="TAS1", name="Task")

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_tags_explicit_empty_clears_existing(offline_session):
    """Test that clearing tags to [] deletes every existing tag id."""
    existing = GeneralTask(
        id="TAS1",
        name="Task",
        tags=[Tag(id="TAG1", tag="A"), Tag(id="TAG2", tag="B")],
    )
    updated = GeneralTask(id="TAS1", name="Task", tags=[])

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert len(payload.data) == 2
    assert all(
        op["operation"] == PatchOperation.DELETE and op["attribute"] == "tagId"
        for op in payload.data
    )
    assert {op["oldValue"][0] for op in payload.data} == {"TAG1", "TAG2"}


def test_tags_add_and_remove(offline_session):
    """Test that a tag swap emits one add op and one delete op, add first."""
    existing = GeneralTask(id="TAS1", name="Task", tags=[Tag(id="TAG1", tag="A")])
    updated = GeneralTask(id="TAS1", name="Task", tags=[Tag(id="TAG2", tag="B")])

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {"operation": PatchOperation.ADD, "attribute": "tagId", "newValue": ["TAG2"]},
        {"operation": PatchOperation.DELETE, "attribute": "tagId", "oldValue": ["TAG1"]},
    ]


def test_tags_unchanged_by_id_is_no_op_even_if_text_differs(offline_session):
    """Test that tags are diffed by id only; a text-only difference is a no-op."""
    existing = GeneralTask(id="TAS1", name="Task", tags=[Tag(id="TAG1", tag="A")])
    updated = GeneralTask(id="TAS1", name="Task", tags=[Tag(id="TAG1", tag="A-renamed")])

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


# ---------------------------------------------------------------------------
# generate_adv_patch_payload -- project
# ---------------------------------------------------------------------------


def test_project_unset_emits_no_op(offline_session):
    """Test that an omitted project is left untouched."""
    existing = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))
    updated = GeneralTask(id="TAS1", name="Task")

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_project_explicit_none_emits_delete(offline_session):
    """Test that clearing project emits a delete op with the old project id."""
    existing = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))
    updated = GeneralTask(id="TAS1", name="Task", project=None)

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {"operation": PatchOperation.DELETE, "attribute": "projectId", "oldValue": "PRO1"}
    ]


def test_project_add_when_previously_unset(offline_session):
    """Test that setting a project when there was none emits an add op."""
    existing = GeneralTask(id="TAS1", name="Task")
    updated = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {"operation": PatchOperation.ADD, "attribute": "projectId", "newValue": "PRO1"}
    ]


def test_project_update_when_id_changes(offline_session):
    """Test that reassigning to a different project emits an update op."""
    existing = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))
    updated = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO2"))

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == [
        {
            "operation": PatchOperation.UPDATE,
            "attribute": "projectId",
            "oldValue": "PRO1",
            "newValue": "PRO2",
        }
    ]


def test_project_unchanged_is_no_op(offline_session):
    """Test that an unchanged project id emits no operation."""
    existing = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))
    updated = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO1"))

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.data == []


def test_project_raises_when_existing_has_multiple_projects(offline_session):
    """Test that updating project is rejected when the task has multiple projects."""
    existing = GeneralTask(
        id="TAS1", name="Task", project=[EntityLink(id="PRO1"), EntityLink(id="PRO2")]
    )
    updated = GeneralTask(id="TAS1", name="Task", project=EntityLink(id="PRO3"))

    with pytest.raises(ValueError, match="multiple associated projects"):
        _payload(offline_session, existing=existing, updated=updated)


# ---------------------------------------------------------------------------
# generate_adv_patch_payload -- combined with base fields
# ---------------------------------------------------------------------------


def test_base_and_special_fields_combine_in_one_payload(offline_session):
    """Test that a base field diff and a special-attribute diff both land in one payload."""
    existing = GeneralTask(id="TAS1", name="Old Name", tags=[Tag(id="TAG1", tag="A")])
    updated = GeneralTask(id="TAS1", name="New Name", tags=[])

    payload = _payload(offline_session, existing=existing, updated=updated)

    assert payload.id == "TAS1"
    assert len(payload.data) == 2
    name_op, tags_op = payload.data
    assert name_op.attribute == "name"
    assert name_op.operation == PatchOperation.UPDATE
    assert name_op.old_value == "Old Name"
    assert name_op.new_value == "New Name"
    assert tags_op == {
        "operation": PatchOperation.DELETE,
        "attribute": "tagId",
        "oldValue": ["TAG1"],
    }


# ---------------------------------------------------------------------------
# determine_extension
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        pytest.param(None, None, id="none"),
        pytest.param("report.CSV", "csv", id="uppercase-extension-lowered"),
        pytest.param("archive.tar.gz", "gz", id="only-last-suffix"),
        pytest.param("README", "", id="no-extension"),
        pytest.param(".hidden", "", id="dotfile-has-no-suffix"),
    ],
)
def test_determine_extension(filename, expected):
    """Test extension extraction across filenames with and without a suffix."""
    assert determine_extension(filename=filename) == expected


# ---------------------------------------------------------------------------
# extract_extensions_from_attachment
# ---------------------------------------------------------------------------


def test_extract_extensions_returns_empty_set_for_none_attachment():
    """Test that a None attachment yields an empty extension set."""
    assert extract_extensions_from_attachment(attachment=None) == set()


def test_extract_extensions_returns_empty_set_when_metadata_missing():
    """Test that an attachment with no metadata yields an empty extension set."""
    attachment = types.SimpleNamespace(metadata=None)
    assert extract_extensions_from_attachment(attachment=attachment) == set()


def test_extract_extensions_returns_empty_set_when_extensions_missing_or_empty():
    """Test that missing or empty metadata.extensions yields an empty extension set."""
    attachment = types.SimpleNamespace(metadata=AttachmentMetadata(extensions=None))
    assert extract_extensions_from_attachment(attachment=attachment) == set()

    attachment = types.SimpleNamespace(metadata=AttachmentMetadata(extensions=[]))
    assert extract_extensions_from_attachment(attachment=attachment) == set()


def test_extract_extensions_lowercases_and_strips_leading_dot():
    """Test that extension names are lowercased and stripped of a leading dot."""
    attachment = types.SimpleNamespace(
        metadata=AttachmentMetadata(
            extensions=[
                EntityLinkWithName(id="X", name=".CSV"),
                EntityLinkWithName(id="Y", name="TXT"),
            ]
        )
    )

    assert extract_extensions_from_attachment(attachment=attachment) == {"csv", "txt"}


def test_extract_extensions_skips_entries_with_non_string_name():
    """Test that an extension entry without a string name is skipped, not raised."""
    metadata = AttachmentMetadata.model_construct(
        extensions=[
            types.SimpleNamespace(name=123),
            EntityLinkWithName(id="Y", name="csv"),
        ]
    )
    attachment = types.SimpleNamespace(metadata=metadata)

    assert extract_extensions_from_attachment(attachment=attachment) == {"csv"}


# ---------------------------------------------------------------------------
# is_metadata_item_list
# ---------------------------------------------------------------------------


def test_is_metadata_item_list_false_for_non_metadata_field():
    """Test that a field not prefixed with 'Metadata.' is never list-typed."""
    existing = GeneralTask(id="TAS1", name="Task")
    updated = GeneralTask(id="TAS1", name="Task")

    assert (
        is_metadata_item_list(
            existing_object=existing, updated_object=updated, metadata_field="name"
        )
        is False
    )


def test_is_metadata_item_list_true_when_existing_value_is_a_list():
    """Test that a list-valued existing metadata entry is detected."""
    existing = GeneralTask(id="TAS1", name="Task", metadata={"colors": [EntityLink(id="LST1")]})
    updated = GeneralTask(id="TAS1", name="Task", metadata={})

    assert (
        is_metadata_item_list(
            existing_object=existing, updated_object=updated, metadata_field="Metadata.colors"
        )
        is True
    )


def test_is_metadata_item_list_true_when_updated_value_is_a_list():
    """Test that a list-valued updated metadata entry is detected even if existing is not."""
    existing = GeneralTask(id="TAS1", name="Task", metadata={"colors": "red"})
    updated = GeneralTask(id="TAS1", name="Task", metadata={"colors": [EntityLink(id="LST1")]})

    assert (
        is_metadata_item_list(
            existing_object=existing, updated_object=updated, metadata_field="Metadata.colors"
        )
        is True
    )


def test_is_metadata_item_list_false_when_neither_value_is_a_list():
    """Test that scalar metadata values on both sides are not list-typed."""
    existing = GeneralTask(id="TAS1", name="Task", metadata={"colors": "red"})
    updated = GeneralTask(id="TAS1", name="Task", metadata={"colors": "blue"})

    assert (
        is_metadata_item_list(
            existing_object=existing, updated_object=updated, metadata_field="Metadata.colors"
        )
        is False
    )


def test_is_metadata_item_list_initializes_none_metadata_to_empty_dict():
    """Test that a None metadata dict is coerced to {} rather than raising."""
    existing = GeneralTask.model_construct(id="TAS1", name="Task", metadata=None)
    updated = GeneralTask.model_construct(id="TAS1", name="Task", metadata=None)

    result = is_metadata_item_list(
        existing_object=existing, updated_object=updated, metadata_field="Metadata.colors"
    )

    assert result is False
    assert existing.metadata == {}
    assert updated.metadata == {}


# ---------------------------------------------------------------------------
# build_property_payload
# ---------------------------------------------------------------------------


def _column(data_column_id: str, sequence: str) -> DataColumnValue:
    return DataColumnValue(data_column_id=data_column_id, sequence=sequence)


def test_build_property_payload_creates_one_property_per_mapped_value():
    """Test that each mapped CSV value becomes a TaskPropertyCreate for its column."""
    columns = [_column("DAC1", "1"), _column("DAC2", "2")]
    rows = [{"col0": "12.5", "col1": "red"}]
    mapping = {"DAC1": "col0", "DAC2": "col1"}

    properties = build_property_payload(
        data_rows=rows,
        column_to_csv_key=mapping,
        data_columns=columns,
        interval="default",
        data_template_id="DAT1",
    )

    assert len(properties) == 2
    prop = next(p for p in properties if p.data_column.data_column_id == "DAC1")
    assert prop.value == "12.5"
    assert prop.visible_trial_number == 1
    assert prop.interval_combination == "default"
    assert prop.data_template == EntityLink(id="DAT1")
    assert prop.data_column.column_sequence == "1"


@pytest.mark.parametrize("value", [None, ""], ids=["none", "empty-string"])
def test_build_property_payload_skips_missing_values(value):
    """Test that a None or empty-string cell value produces no property."""
    properties = build_property_payload(
        data_rows=[{"col0": value}],
        column_to_csv_key={"DAC1": "col0"},
        data_columns=[_column("DAC1", "1")],
        interval="default",
        data_template_id="DAT1",
    )

    assert properties == []


def test_build_property_payload_skips_mapping_with_no_matching_column():
    """Test that a mapping entry pointing at an unknown column id produces no property."""
    properties = build_property_payload(
        data_rows=[{"col0": "5"}],
        column_to_csv_key={"DAC-unknown": "col0"},
        data_columns=[_column("DAC1", "1")],
        interval="default",
        data_template_id="DAT1",
    )

    assert properties == []


def test_build_property_payload_ignores_falsy_columns():
    """Test that a None entry in data_columns does not break lookup construction."""
    properties = build_property_payload(
        data_rows=[{"col0": "5"}],
        column_to_csv_key={"DAC1": "col0"},
        data_columns=[None],
        interval="default",
        data_template_id="DAT1",
    )

    assert properties == []


def test_build_property_payload_multiple_rows_increment_trial_number():
    """Test that visible_trial_number increments per row, starting at 1."""
    properties = build_property_payload(
        data_rows=[{"col0": "1"}, {"col0": "2"}, {"col0": "3"}],
        column_to_csv_key={"DAC1": "col0"},
        data_columns=[_column("DAC1", "1")],
        interval="default",
        data_template_id="DAT1",
    )

    assert [p.visible_trial_number for p in properties] == [1, 2, 3]
    assert [p.value for p in properties] == ["1", "2", "3"]


# ---------------------------------------------------------------------------
# build_task_metadata
# ---------------------------------------------------------------------------


def test_build_task_metadata_builds_inventories_and_blockdata():
    """Test that task metadata rolls up inventories, data templates, and workflows."""
    block = Block(
        id="BLK1",
        workflow=[EntityLink(id="WFL1", name="Workflow A")],
        data_template=[EntityLink(id="DAT1", name="Data Template A")],
    )
    task = PropertyTask(
        id="TAS1",
        name="Task",
        blocks=[block],
        inventory_information=[TaskInventoryInformation(inventory_id="INV1", lot_id="LOT1")],
    )

    metadata = build_task_metadata(task=task, block_id="BLK1", filename="results.csv")

    assert metadata.filename == "results.csv"
    assert metadata.task_id == "TAS1"
    assert metadata.block_id == "BLK1"
    assert len(metadata.inventories) == 1
    assert metadata.inventories[0].inventory_id == "INV1"
    assert metadata.inventories[0].lot_id == "LOT1"
    assert metadata.blockdata.id == "BLK1"
    assert [dt.id for dt in metadata.blockdata.datatemplate] == ["DAT1"]
    assert [dt.name for dt in metadata.blockdata.datatemplate] == ["Data Template A"]
    assert [wf.albert_id for wf in metadata.blockdata.workflow] == ["WFL1"]
    assert [wf.name for wf in metadata.blockdata.workflow] == ["Workflow A"]


def test_build_task_metadata_raises_when_block_not_found():
    """Test that requesting metadata for a missing block id raises ValueError."""
    task = PropertyTask(id="TAS1", name="Task", blocks=[])

    with pytest.raises(ValueError, match="not found"):
        build_task_metadata(task=task, block_id="BLK1", filename=None)


def test_build_task_metadata_defaults_inventories_to_empty_list():
    """Test that a task with no inventory_information produces an empty inventories list."""
    block = Block(
        id="BLK1",
        workflow=[EntityLink(id="WFL1", name="Workflow A")],
        data_template=[EntityLink(id="DAT1", name="Data Template A")],
    )
    task = PropertyTask(id="TAS1", name="Task", blocks=[block])

    metadata = build_task_metadata(task=task, block_id="BLK1", filename=None)

    assert metadata.inventories == []


# ---------------------------------------------------------------------------
# resolve_attachment
# ---------------------------------------------------------------------------


class _FakeAttachmentCollection:
    """Narrow stand-in exposing only the one method resolve_attachment calls."""

    def __init__(self, note: Note | None):
        self._note = note
        self.calls: list[dict] = []

    def upload_and_attach_file_as_note(
        self,
        parent_id,
        file_data,
        note_text="",
        file_name="",
        upload_key=None,
        content_type=None,
    ):
        self.calls.append(
            {
                "parent_id": parent_id,
                "note_text": note_text,
                "file_name": file_name,
                "upload_key": upload_key,
                "content_type": content_type,
            }
        )
        return self._note


def test_resolve_attachment_uploads_file_and_returns_new_attachment_id(tmp_path):
    """Test that a valid file path is uploaded and its first attachment id is returned."""
    file_path = tmp_path / "results.csv"
    file_path.write_text("a,b\n1,2\n")
    note = Note(
        parent_id="TAS1",
        note="uploaded",
        attachments=[NoteAttachmentEntityLink(id="ATT1", name="results.csv")],
    )
    fake_collection = _FakeAttachmentCollection(note)

    attachment_id = resolve_attachment(
        attachment_collection=fake_collection,
        task_id="TAS1",
        file_path=file_path,
        attachment_id=None,
        allowed_extensions={"csv"},
        note_text="Attaching results",
    )

    assert attachment_id == "ATT1"
    assert fake_collection.calls == [
        {
            "parent_id": "TAS1",
            "note_text": "Attaching results",
            "file_name": "results.csv",
            "upload_key": None,
            "content_type": None,
        }
    ]


def test_resolve_attachment_missing_file_raises_file_not_found_error(tmp_path):
    """Test that a nonexistent file path raises FileNotFoundError."""
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        resolve_attachment(
            attachment_collection=_FakeAttachmentCollection(None),
            task_id="TAS1",
            file_path=missing_path,
            attachment_id=None,
            allowed_extensions={"csv"},
            note_text=None,
        )


def test_resolve_attachment_disallowed_extension_raises_value_error(tmp_path):
    """Test that a file with a disallowed extension raises ValueError."""
    file_path = tmp_path / "results.txt"
    file_path.write_text("data")

    with pytest.raises(ValueError, match="not permitted"):
        resolve_attachment(
            attachment_collection=_FakeAttachmentCollection(None),
            task_id="TAS1",
            file_path=file_path,
            attachment_id=None,
            allowed_extensions={"csv"},
            note_text=None,
        )


def test_resolve_attachment_empty_allowed_extensions_skips_check(tmp_path):
    """Test that an empty allowed_extensions set skips the extension check entirely."""
    file_path = tmp_path / "results.txt"
    file_path.write_text("data")
    note = Note(
        parent_id="TAS1",
        note="uploaded",
        attachments=[NoteAttachmentEntityLink(id="ATT1", name="results.txt")],
    )

    attachment_id = resolve_attachment(
        attachment_collection=_FakeAttachmentCollection(note),
        task_id="TAS1",
        file_path=file_path,
        attachment_id=None,
        allowed_extensions=set(),
        note_text=None,
    )

    assert attachment_id == "ATT1"


def test_resolve_attachment_no_file_path_returns_given_attachment_id():
    """Test that omitting file_path returns the caller-supplied attachment_id as-is."""
    attachment_id = resolve_attachment(
        attachment_collection=_FakeAttachmentCollection(None),
        task_id="TAS1",
        file_path=None,
        attachment_id="ATT9",
        allowed_extensions={"csv"},
        note_text=None,
    )

    assert attachment_id == "ATT9"


def test_resolve_attachment_neither_file_path_nor_attachment_id_raises():
    """Test that omitting both file_path and attachment_id raises ValueError."""
    with pytest.raises(ValueError, match="attachment_id must be provided"):
        resolve_attachment(
            attachment_collection=_FakeAttachmentCollection(None),
            task_id="TAS1",
            file_path=None,
            attachment_id=None,
            allowed_extensions={"csv"},
            note_text=None,
        )


def test_resolve_attachment_upload_without_attachments_raises_value_error(tmp_path):
    """Test that an upload response with no attachments raises ValueError."""
    file_path = tmp_path / "results.csv"
    file_path.write_text("a,b\n1,2\n")
    note = Note(parent_id="TAS1", note="uploaded", attachments=[])

    with pytest.raises(ValueError, match="Failed to upload attachment"):
        resolve_attachment(
            attachment_collection=_FakeAttachmentCollection(note),
            task_id="TAS1",
            file_path=file_path,
            attachment_id=None,
            allowed_extensions={"csv"},
            note_text=None,
        )


# ---------------------------------------------------------------------------
# fetch_csv_table_rows
# ---------------------------------------------------------------------------


@responses.activate
def test_fetch_csv_table_rows_returns_rows_under_first_key(offline_session):
    """Test that the rows under the response's first key are returned."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/csvtables/ATT1",
        json={"rows": [{"col0": "a"}, {"col0": "b"}]},
    )

    rows = fetch_csv_table_rows(session=offline_session, attachment_id="ATT1")

    assert rows == [{"col0": "a"}, {"col0": "b"}]


@responses.activate
def test_fetch_csv_table_rows_headers_only_hits_headers_endpoint(offline_session):
    """Test that headers_only=True queries the dedicated headers endpoint."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/csvtables/ATT1/headers",
        json={"rows": [{"col0": "Header A"}]},
    )

    rows = fetch_csv_table_rows(session=offline_session, attachment_id="ATT1", headers_only=True)

    assert rows == [{"col0": "Header A"}]


@responses.activate
def test_fetch_csv_table_rows_empty_response_raises_value_error(offline_session):
    """Test that an empty CSV preview response raises ValueError."""
    responses.get(f"{UNIT_BASE_URL}/api/v3/csvtables/ATT1", json={})

    with pytest.raises(ValueError, match="empty"):
        fetch_csv_table_rows(session=offline_session, attachment_id="ATT1")


@responses.activate
def test_fetch_csv_table_rows_non_list_rows_raises_value_error(offline_session):
    """Test that a non-list value under the first key raises ValueError."""
    responses.get(f"{UNIT_BASE_URL}/api/v3/csvtables/ATT1", json={"rows": "not-a-list"})

    with pytest.raises(ValueError, match="header row"):
        fetch_csv_table_rows(session=offline_session, attachment_id="ATT1")


# ---------------------------------------------------------------------------
# map_csv_headers_to_columns
# ---------------------------------------------------------------------------


def _col(data_column_id: str, name: str | None, *, hidden: bool = False) -> DataColumnValue:
    return DataColumnValue(data_column_id=data_column_id, name=name, hidden=hidden)


def test_auto_matches_case_insensitive_header_to_column_name():
    """Test that a CSV header is matched to a column name case-insensitively."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "viscosity")],
        data_columns=[_col("DAC1", "Viscosity")],
    )

    assert mapping == {"DAC1": "col0"}


def test_hidden_columns_are_excluded_from_matching():
    """Test that a hidden column is never auto-matched to a CSV header."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Viscosity")],
        data_columns=[_col("DAC1", "Viscosity", hidden=True)],
    )

    assert mapping == {}


def test_duplicate_column_names_only_first_is_mapped(caplog):
    """Test that only the first of two same-named columns is eligible for matching."""
    with caplog.at_level("WARNING"):
        mapping = map_csv_headers_to_columns(
            header_sequence=[("col0", "Viscosity")],
            data_columns=[_col("DAC1", "Viscosity"), _col("DAC2", "Viscosity")],
        )

    assert mapping == {"DAC1": "col0"}
    assert any("Viscosity" in record.message for record in caplog.records)


def test_columns_without_name_or_id_are_ignored():
    """Test that columns missing a name or an id never participate in matching."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Foo")],
        data_columns=[
            DataColumnValue(data_column_id="DAC1", name=None),
            DataColumnValue.model_construct(data_column_id=None, name="Foo"),
        ],
    )

    assert mapping == {}


def test_field_mapping_overrides_auto_detection():
    """Test that explicit field_mapping entries (csv_to_column) drive the result."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Visc (cP)"), ("col1", "Dens (g/mL)")],
        data_columns=[_col("DAC1", "Viscosity"), _col("DAC2", "Density")],
        field_mapping={"Visc (cP)": "Viscosity", "Dens (g/mL)": "Density"},
    )

    assert mapping == {"DAC1": "col0", "DAC2": "col1"}


def test_field_mapping_column_to_csv_direction_is_inverted():
    """Test that mapping_direction='column_to_csv' interprets field_mapping in reverse."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Visc (cP)")],
        data_columns=[_col("DAC1", "Viscosity")],
        field_mapping={"Viscosity": "Visc (cP)"},
        mapping_direction="column_to_csv",
    )

    assert mapping == {"DAC1": "col0"}


def test_field_mapping_non_string_entries_raise_value_error():
    """Test that a non-string field_mapping key or value raises ValueError."""
    with pytest.raises(ValueError, match="strings"):
        map_csv_headers_to_columns(
            header_sequence=[("col0", "Viscosity")],
            data_columns=[_col("DAC1", "Viscosity")],
            field_mapping={"Viscosity": 123},
        )


def test_field_mapping_unmatched_header_falls_back_to_auto_match():
    """Test that a field_mapping entry for a missing CSV header is skipped, not fatal."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Viscosity")],
        data_columns=[_col("DAC1", "Viscosity")],
        field_mapping={"Missing Header": "Viscosity"},
    )

    assert mapping == {"DAC1": "col0"}


def test_field_mapping_unmatched_column_falls_back_to_auto_match():
    """Test that a field_mapping entry for a missing column is skipped, not fatal."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Viscosity")],
        data_columns=[_col("DAC1", "Viscosity")],
        field_mapping={"Viscosity": "Missing Column"},
    )

    assert mapping == {"DAC1": "col0"}


def test_field_mapping_second_entry_for_already_mapped_column_is_skipped():
    """Test that once a column is mapped, a later field_mapping entry cannot remap it."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "H1"), ("col1", "H2")],
        data_columns=[_col("DAC1", "Viscosity")],
        field_mapping={"H1": "Viscosity", "H2": "Viscosity"},
    )

    assert mapping == {"DAC1": "col0"}


def test_auto_match_skips_header_already_consumed_by_field_mapping():
    """Test that a header already mapped explicitly is not reconsidered in auto-match."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Viscosity")],
        data_columns=[_col("DAC1", "Viscosity")],
        field_mapping={"Viscosity": "Viscosity"},
    )

    assert mapping == {"DAC1": "col0"}


def test_auto_match_no_matching_column_is_skipped():
    """Test that a CSV header with no matching column name is simply skipped."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Unrelated Header")],
        data_columns=[_col("DAC1", "Viscosity")],
    )

    assert mapping == {}


def test_auto_match_skips_when_column_already_used():
    """Test that a second header matching an already-mapped column name is skipped."""
    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "Viscosity"), ("col1", "viscosity")],
        data_columns=[_col("DAC1", "Viscosity")],
    )

    assert mapping == {"DAC1": "col0"}


def test_curve_mode_maps_by_curve_entry_name():
    """Test that use_curve_data_ids maps against curve_data entries, not the column name."""
    column = DataColumnValue(
        data_column_id="DAC1",
        name="Curve Col",
        curve_data=[
            CurveDataEntityLink(id="DAC2", name="X Values"),
            CurveDataEntityLink(id="DAC3", name="Y Values"),
        ],
    )

    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "x values"), ("col1", "y values")],
        data_columns=[column],
        use_curve_data_ids=True,
    )

    assert mapping == {"DAC2": "col0", "DAC3": "col1"}


def test_curve_mode_duplicate_curve_names_only_first_mapped():
    """Test that two curve entries sharing a name only map the first one seen."""
    column_a = DataColumnValue(
        data_column_id="DAC1", curve_data=[CurveDataEntityLink(id="DAC2", name="X")]
    )
    column_b = DataColumnValue(
        data_column_id="DAC4", curve_data=[CurveDataEntityLink(id="DAC5", name="X")]
    )

    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "X")],
        data_columns=[column_a, column_b],
        use_curve_data_ids=True,
    )

    assert mapping == {"DAC2": "col0"}


def test_curve_mode_entries_missing_name_or_id_are_skipped():
    """Test that a curve_data entry missing an id or name is ignored, not matched."""
    column = DataColumnValue(
        data_column_id="DAC1",
        curve_data=[
            CurveDataEntityLink.model_construct(id=None, name="X"),
            CurveDataEntityLink(id="DAC2", name="Y"),
        ],
    )

    mapping = map_csv_headers_to_columns(
        header_sequence=[("col0", "X"), ("col1", "Y")],
        data_columns=[column],
        use_curve_data_ids=True,
    )

    assert mapping == {"DAC2": "col1"}
