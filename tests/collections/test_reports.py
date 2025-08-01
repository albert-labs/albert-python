"""
Tests for the FullAnalyticalReport resource and related functionality.
"""

import pandas as pd
import pytest

from albert.client import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.projects import Project
from albert.resources.reports import (
    FullAnalyticalReport,
)
from albert.resources.tasks import BaseTask


@pytest.mark.skip(reason="Report Queries not loaded into testing environment yet")
def test_get_raw_dataframe(
    client: Albert,
    seeded_reports: list[FullAnalyticalReport],
    seeded_products: list[InventoryItem],  # needed to load in data
    seeded_projects: list[Project],  # needed to load in data
    seeded_tasks: list[BaseTask],  # needed to load in data
):
    """Test getting raw data as DataFrame."""
    full_report = client.reports.get_full_report(id=seeded_reports[0].id)
    df = full_report.get_raw_dataframe()
    assert isinstance(df, pd.DataFrame)
