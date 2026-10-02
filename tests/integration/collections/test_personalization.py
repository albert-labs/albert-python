from contextlib import suppress

import pytest

from albert.client import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import NotFoundError
from albert.resources.personalization import Personalization, PersonalizationCategory
from albert.resources.projects import Project

pytestmark = pytest.mark.xdist_group("projects")


def test_personalization_crud(client: Albert, seeded_locations, seed_prefix: str):
    """Test creating, reading, listing, and deleting a personalization record."""
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - Personalization Target",
            locations=[EntityLink(id=seeded_locations[1].id)],
        )
    )
    record = None
    try:
        record = client.personalization.create(
            personalization=Personalization(
                category=PersonalizationCategory.STARRED_PROJECTS,
                saved_id=project.id,
                saved_name=project.description,
            )
        )
        assert record.id and record.id.startswith("USP")
        assert record.category is PersonalizationCategory.STARRED_PROJECTS
        assert record.saved_id == project.id

        fetched = client.personalization.get_by_id(id=record.id)
        assert fetched.id == record.id
        assert fetched.saved_id == project.id

        starred = list(
            client.personalization.get_all(category=PersonalizationCategory.STARRED_PROJECTS)
        )
        assert record.id in {r.id for r in starred}
        assert all(r.category is PersonalizationCategory.STARRED_PROJECTS for r in starred)

        client.personalization.delete(id=record.id)
        record, deleted_id = None, record.id
        with pytest.raises(NotFoundError):
            client.personalization.get_by_id(id=deleted_id)
    finally:
        if record is not None:
            with suppress(NotFoundError):
                client.personalization.delete(id=record.id)
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)
