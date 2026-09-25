import pytest

from albert import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.worksheets import Worksheet
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("sheets")


def test_get_worksheet(seeded_worksheet: Worksheet):
    assert isinstance(seeded_worksheet, Worksheet)
    assert isinstance(seeded_worksheet.project_id, str)


def test_add_sheet(client: Albert, seeded_worksheet: Worksheet):
    existing_number = len(seeded_worksheet.sheets)
    updated_worksheet = client.worksheets.add_sheet(
        project_id=seeded_worksheet.project_id, sheet_name="New sheet I just added"
    )
    assert isinstance(updated_worksheet, Worksheet)
    assert len(updated_worksheet.sheets) == existing_number + 1


def test_worksheet_search(
    client: Albert,
    seed_prefix: str,
    seeded_worksheet: Worksheet,
    seeded_products: list[InventoryItem],
):
    """Test worksheet search finds a seeded formula within its project."""
    seeded_ids = {p.id for p in seeded_products}
    hits = poll_until(
        lambda: [
            hit
            for hit in client.worksheets.search(
                text=seed_prefix,
                project_id=seeded_worksheet.project_id,
                max_items=50,
            )
            if hit.id in seeded_ids
        ]
    )
    assert hits, "Expected seeded formula in worksheet search results"
    assert hits[0].id in seeded_ids


# Need to seed a Sheet Template First
# def test_setup_new_sheet_from_template(client: Albert, seeded_worksheet: Worksheet):
#     existing_number = len(seeded_worksheet.sheets)
#     updated_worksheet = client.worksheets.setup_new_sheet_from_template(
#         project_id=seeded_worksheet.project_id,
#         sheet_template_id=seeded_worksheet.sheets[0].id,
#         sheet_name="New sheet from template",
#     )
#     assert isinstance(updated_worksheet, Worksheet)
#     assert len(updated_worksheet.sheets) == existing_number + 1
