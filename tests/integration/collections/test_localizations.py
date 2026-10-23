from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.data_templates import DataTemplate
from albert.resources.localizations import (
    Localization,
    LocalizationLanguage,
    LocalizationPatchDatum,
)

pytestmark = pytest.mark.xdist_group("datatemplates")


def test_get_all_by_id(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test reading the localizations of a seeded data template."""
    template = seeded_data_templates[0]
    rows = client.localizations.get_all_by_id(id=template.id)

    assert len(rows) >= 1
    for row in rows:
        assert isinstance(row, Localization)
        assert row.id == template.id
    assert rows[0].unique_id == "DAT"
    assert rows[0].name == template.name


def test_update(client: Albert, seed_prefix: str):
    """Test adding, changing, and removing a translation on a private data template."""
    dt = client.data_templates.create(
        data_template=DataTemplate(name=f"{seed_prefix} - Localization Test")
    )
    try:
        client.localizations.update(
            id=dt.id,
            patches=[
                LocalizationPatchDatum(
                    operation="add",
                    attribute="name",
                    language=LocalizationLanguage.GERMAN,
                    unique_id="DAT",
                    new_value="Testvorlage",
                )
            ],
        )
        rows = client.localizations.get_all_by_id(id=dt.id)
        main = next(row for row in rows if row.unique_id == "DAT")
        assert main.localization == {"name": {"de": "Testvorlage"}}

        client.localizations.update(
            id=dt.id,
            patches=[
                LocalizationPatchDatum(
                    operation="update",
                    attribute="name",
                    language="de",
                    unique_id="DAT",
                    old_value="Testvorlage",
                    new_value="Neue Testvorlage",
                )
            ],
        )
        main = next(
            row for row in client.localizations.get_all_by_id(id=dt.id) if row.unique_id == "DAT"
        )
        assert main.localization == {"name": {"de": "Neue Testvorlage"}}

        client.localizations.update(
            id=dt.id,
            patches=[
                LocalizationPatchDatum(
                    operation="delete",
                    attribute="name",
                    language="de",
                    unique_id="DAT",
                    old_value="Neue Testvorlage",
                )
            ],
        )
        main = next(
            row for row in client.localizations.get_all_by_id(id=dt.id) if row.unique_id == "DAT"
        )
        assert main.localization is None or "de" not in main.localization.get("name", {})
    finally:
        with suppress(NotFoundError):
            client.data_templates.delete(id=dt.id)
