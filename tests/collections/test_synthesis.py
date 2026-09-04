from contextlib import suppress

import pytest

from albert import Albert
from albert.exceptions import AlbertException
from albert.resources.notebooks import Notebook
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("projects")


def test_synthesis_search(client: Albert, seed_prefix: str, seeded_notebooks: list[Notebook]):
    """Test search finds a newly created synthesis record and its ID is usable."""
    synthesis = client.synthesis.create(
        parent_id=seeded_notebooks[0].id,
        name=f"{seed_prefix} amide coupling",
    )
    try:
        hits = poll_until(
            lambda: [
                item
                for item in client.synthesis.search(text=seed_prefix, max_items=50)
                if item.id == synthesis.id
            ]
        )
        assert hits, "Expected created synthesis in search results"
        hit = hits[0]
        assert hit.id == synthesis.id

        fetched = client.synthesis.get_by_id(id=hit.id)
        assert fetched.id == synthesis.id
    finally:
        with suppress(AlbertException):
            client.session.delete(url=f"{client.synthesis.base_path}/{synthesis.id}")
