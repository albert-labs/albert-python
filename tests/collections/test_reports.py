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
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("tasks")


def test_search_reports(
    client: Albert,
    seed_prefix: str,
    seeded_reports: list[FullAnalyticalReport],
):
    """Test searching reports finds seeded reports and hits hydrate."""
    expected = seeded_reports[0]
    seeded_ids = {r.id for r in seeded_reports}
    hits = poll_until(
        lambda: [
            hit
            for hit in client.reports.search(text=seed_prefix, max_items=50)
            if hit.id in seeded_ids
        ]
    )
    hit_ids = {hit.id for hit in hits}
    assert expected.id in hit_ids

    hydrated = next(hit for hit in hits if hit.id == expected.id).hydrate()
    assert isinstance(hydrated, FullAnalyticalReport)
    assert hydrated.id == expected.id


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
