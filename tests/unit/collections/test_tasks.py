"""Unit tests for TaskCollection private helpers."""

import pytest

from albert.collections.tasks import TaskCollection
from albert.resources.tasks import BatchTask, PropertyTask


def test_import_results_rejects_batch_task():
    """Test that importing results into a batch task raises a clear error."""
    task = BatchTask(id="TAS1", name="Batch", parent_id="PRO1")

    with pytest.raises(ValueError, match="TAS1 is a batch task"):
        TaskCollection._ensure_import_results_supported(task=task)


def test_import_results_accepts_property_task():
    """Test that a property task is accepted for importing results."""
    task = PropertyTask(id="TAS2", name="Property", parent_id="PRO1")

    TaskCollection._ensure_import_results_supported(task=task)
