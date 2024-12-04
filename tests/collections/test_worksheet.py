from albert.resources.worksheets import Worksheet


def test_get_worksheet(seeded_worksheet: Worksheet):
    assert isinstance(seeded_worksheet, Worksheet)
    assert isinstance(seeded_worksheet.project_id, str)
