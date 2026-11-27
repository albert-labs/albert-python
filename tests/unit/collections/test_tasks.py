"""Unit tests for TaskCollection private helpers."""

import pytest

from albert.collections.tasks import TaskCollection
from albert.resources.tasks import BatchTask, Block, PropertyTask
from albert.resources.workflows import Workflow


def test_import_results_rejects_batch_task():
    """Test that importing results into a batch task raises a clear error."""
    task = BatchTask(id="TAS1", name="Batch", parent_id="PRO1")

    with pytest.raises(ValueError, match="TAS1 is a batch task"):
        TaskCollection._ensure_import_results_supported(task=task)


def test_import_results_accepts_property_task():
    """Test that a property task is accepted for importing results."""
    task = PropertyTask(id="TAS2", name="Property", parent_id="PRO1")

    TaskCollection._ensure_import_results_supported(task=task)


def _block_with_workflows(*workflows: Workflow) -> Block:
    return Block(
        id="BLK1",
        workflow=list(workflows),
        data_template=[{"id": "DAT1"}],
    )


@pytest.mark.parametrize("placeholder_first", [True, False])
def test_get_block_current_workflow_id_prefers_final_placeholder_over_real_initial(
    placeholder_first: bool,
):
    """Test that a final placeholder wins over a real initial workflow in any order."""
    placeholder = Workflow(id="WFL1", name="No Parameter Group", category="FINAL")
    initial = Workflow(id="WFL7108", category="INITIAL")
    workflows = [placeholder, initial] if placeholder_first else [initial, placeholder]
    block = _block_with_workflows(*workflows)

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL1"


@pytest.mark.parametrize("final_first", [True, False])
def test_get_block_current_workflow_id_prefers_final_over_initial(final_first: bool):
    """Test that the final workflow wins over the initial one in any order."""
    final = Workflow(id="WFL2", category="FINAL")
    initial = Workflow(id="WFL3", category="INITIAL")
    workflows = [final, initial] if final_first else [initial, final]
    block = _block_with_workflows(*workflows)

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL2"


def test_get_block_current_workflow_id_skips_uncategorized_placeholder():
    """Test that the placeholder is skipped for a real workflow when no categories exist."""
    block = _block_with_workflows(
        Workflow(id="WFL1", name="No Parameter Group"),
        Workflow(id="WFL2"),
    )

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL2"


def test_get_block_current_workflow_id_keeps_placeholder_when_it_is_the_only_workflow():
    """Test that a lone placeholder is returned rather than skipped."""
    block = _block_with_workflows(Workflow(id="WFL1", name="No Parameter Group"))

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL1"


def test_get_block_current_workflow_id_falls_back_to_initial():
    """Test that an initial-only block resolves to the initial workflow."""
    block = _block_with_workflows(Workflow(id="WFL7108", category="INITIAL"))

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL7108"


def test_get_block_current_workflow_id_returns_first_when_nothing_is_categorized():
    """Test that the first workflow wins when no categories or placeholder apply."""
    block = _block_with_workflows(Workflow(id="WFL2"), Workflow(id="WFL3"))

    assert TaskCollection._get_block_current_workflow_id(block) == "WFL2"
