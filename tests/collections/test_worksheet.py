from albert import Albert
from albert.resources.worksheets import Worksheet


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
