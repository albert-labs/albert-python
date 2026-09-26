"""Unit tests for ProjectCollection ACL PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_acl_patch_operations`` with no I/O to
fake.
"""

from albert.collections.projects import ProjectCollection
from albert.resources.acls import ACL, AccessControlLevel


def test_no_acl_changes_emit_no_ops(offline_session) -> None:
    """Test that identical ACL lists produce no operations."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []


def test_both_none_emit_no_ops(offline_session) -> None:
    """Test that both ACL lists being None (unset) produces no operations."""
    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=None, updated=None
    )

    assert ops == []


def test_new_acl_entry_emits_add_op_with_full_dump(offline_session) -> None:
    """Test that a newly added ACL entry emits a single add op with the full entry."""
    existing: list[ACL] = []
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "ACL",
            "operation": "add",
            "newValue": [{"id": "USR1", "fgc": "ProjectViewer"}],
        }
    ]


def test_removed_acl_entry_emits_delete_op_with_id_only(offline_session) -> None:
    """Test that a removed ACL entry emits a delete op carrying only its id."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]
    updated: list[ACL] = []

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "ACL",
            "operation": "delete",
            "oldValue": [{"id": "USR1"}],
        }
    ]


def test_changed_fgc_on_existing_entry_emits_fgc_update(offline_session) -> None:
    """Test that changing an existing entry's access level emits a per-id fgc update."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "fgc",
            "id": "USR1",
            "operation": "update",
            "oldValue": "ProjectViewer",
            "newValue": "ProjectEditor",
        }
    ]


def test_unchanged_fgc_on_existing_entry_emits_no_op(offline_session) -> None:
    """Test that an entry present in both lists with the same fgc emits no operation."""
    existing = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]
    updated = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []


def test_add_delete_and_update_combine_in_one_call(offline_session) -> None:
    """Test a mixed add/delete/update ACL diff emits one op per change kind."""
    existing = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]
    updated = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR),  # changed
        ACL(id="USR3", fgc=AccessControlLevel.PROJECT_VIEWER),  # added
        # USR2 removed
    ]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    add_ops = [op for op in ops if op["operation"] == "add"]
    delete_ops = [op for op in ops if op["operation"] == "delete"]
    update_ops = [op for op in ops if op["operation"] == "update"]

    assert add_ops == [
        {
            "attribute": "ACL",
            "operation": "add",
            "newValue": [{"id": "USR3", "fgc": "ProjectViewer"}],
        }
    ]
    assert delete_ops == [
        {
            "attribute": "ACL",
            "operation": "delete",
            "oldValue": [{"id": "USR2"}],
        }
    ]
    assert update_ops == [
        {
            "attribute": "fgc",
            "id": "USR1",
            "operation": "update",
            "oldValue": "ProjectViewer",
            "newValue": "ProjectEditor",
        }
    ]


def test_none_fgc_on_both_sides_emits_no_op(offline_session) -> None:
    """Test that an entry with fgc unset on both sides emits no fgc update."""
    existing = [ACL(id="USR1", fgc=None)]
    updated = [ACL(id="USR1", fgc=None)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []
