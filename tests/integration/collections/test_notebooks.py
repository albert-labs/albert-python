from collections.abc import Iterator

import pytest

from albert import Albert
from albert.exceptions import AlbertException
from albert.resources.notebooks import (
    HeaderBlock,
    HeaderContent,
    Notebook,
    NotebookCopyInfo,
    NotebookCopyType,
    ParagraphBlock,
    ParagraphContent,
)
from albert.resources.projects import Project
from tests.integration.seeding import generate_notebook_block_seeds, generate_notebook_seeds
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("projects")


@pytest.fixture(scope="function")
def seeded_notebook(
    client: Albert, seed_prefix: str, seeded_projects: Iterator[list[Project]]
) -> Iterator[Notebook]:
    notebook = generate_notebook_seeds(seed_prefix=seed_prefix, seeded_projects=seeded_projects)[0]
    seeded = client.notebooks.create(notebook=notebook)
    seeded.blocks = generate_notebook_block_seeds(seed_prefix=seed_prefix)
    yield client.notebooks.update_block_content(notebook=seeded)
    client.notebooks.delete(id=seeded.id)


def test_get_by_id(client: Albert, seeded_notebooks: list[Notebook]):
    nb = seeded_notebooks[0]
    retrieved_nb = client.notebooks.get_by_id(id=nb.id)
    assert retrieved_nb.id == nb.id


def test_list_by_parent_id(client: Albert, seeded_notebooks: list[Notebook]):
    nb = seeded_notebooks[0]
    retrieved_nb = client.notebooks.list_by_parent_id(parent_id=nb.parent_id)[0]
    assert nb.name == retrieved_nb.name


def test_list_by_parent_id_max_items(client: Albert, seeded_notebooks: list[Notebook]):
    """Test that max_items caps the number of notebooks returned."""
    nb = seeded_notebooks[0]
    retrieved = client.notebooks.list_by_parent_id(parent_id=nb.parent_id, max_items=1)
    assert len(retrieved) == 1


def test_update(client: Albert, seeded_notebook: Notebook):
    notebook = seeded_notebook.model_copy()

    marker = "TEST"
    notebook.name = marker

    updated_notebook = client.notebooks.update(notebook=notebook)
    assert updated_notebook.name == notebook.name


def test_update_block_content_with_reorder(client: Albert, seeded_notebook: Notebook):
    marker = list(seeded_notebook.blocks)
    marker[0] = ParagraphBlock(content=ParagraphContent(text="Converted block."))  # Replace block
    marker = marker[::-1]  # reverse blocks
    marker = marker[3:]  # remove some blocks
    seeded_notebook.blocks = marker

    updated_notebook = client.notebooks.update_block_content(notebook=seeded_notebook)
    for updated, existing in zip(updated_notebook.blocks, seeded_notebook.blocks, strict=True):
        assert updated.id == existing.id
        assert updated.content == existing.content


def test_append_blocks(client: Albert, seeded_notebook: Notebook):
    """Test appending blocks preserves existing blocks."""
    existing_ids = [b.id for b in seeded_notebook.blocks]
    new_block = ParagraphBlock(content=ParagraphContent(text="Appended block."))

    updated_notebook = client.notebooks.append_blocks(id=seeded_notebook.id, blocks=[new_block])

    updated_ids = [b.id for b in updated_notebook.blocks]
    assert updated_ids[: len(existing_ids)] == existing_ids
    assert updated_notebook.blocks[-1].content.text == "Appended block."


def test_update_block_content_with_empty_text(client: Albert, seeded_notebook: Notebook):
    # Ensure we can enter blocks with None Fields
    header_block = HeaderBlock(content=HeaderContent(level=1, text=None))
    seeded_notebook.blocks.append(header_block)
    updated_notebook = client.notebooks.update_block_content(notebook=seeded_notebook)
    assert updated_notebook.blocks[-1].content.text is None


def test_search(client: Albert, seed_prefix: str, seeded_notebooks: list[Notebook]):
    """Test search finds seeded notebook block content scoped to the seed project."""
    nb = seeded_notebooks[0]
    hits = poll_until(
        lambda: [
            hit
            for hit in client.notebooks.search(
                text=seed_prefix, project_id=nb.parent_id, max_items=50
            )
            if hit.notebook_id == nb.id and hit.block_id
        ]
    )
    assert hits, "Expected seeded notebook in search results"


def test_get_block_by_id(client: Albert, seeded_notebooks: list[Notebook]):
    nb = seeded_notebooks[0]
    block = nb.blocks[0]
    retrieved_block = client.notebooks.get_block_by_id(notebook_id=nb.id, block_id=block.id)
    assert retrieved_block.id == block.id


def test_create_validation(client: Albert, seeded_projects: Iterator[list[Project]]):
    notebook = Notebook(
        parent_id=seeded_projects[0].id,
        blocks=[ParagraphBlock(content=ParagraphContent(text="test"))],
    )
    with pytest.raises(AlbertException, match="Cannot create a Notebook with pre-filled blocks."):
        client.notebooks.create(notebook=notebook)


def test_copy(client: Albert, seeded_notebook: Notebook, seeded_projects: Iterator[list[Project]]):
    notebook = seeded_notebook.model_copy()

    project: Project = seeded_projects[0]
    np_copy_info = NotebookCopyInfo(
        id=notebook.id,
        parent_id=project.id,
    )

    notebook_copy = client.notebooks.copy(
        notebook_copy_info=np_copy_info, type=NotebookCopyType.PROJECT
    )

    blocks = notebook.blocks
    block_copies = notebook_copy.blocks
    assert len(blocks) == len(block_copies)
    for block, block_copy in zip(blocks, block_copies, strict=True):
        assert type(block) == type(block_copy)


def test_create_block(client: Albert, seeded_notebook: Notebook):
    """Test creating a block adds it to the notebook, preserving existing blocks."""
    existing_ids = {b.id for b in seeded_notebook.blocks}
    new_block = ParagraphBlock(content=ParagraphContent(text="Created in place."))

    created = client.notebooks.create_block(notebook_id=seeded_notebook.id, block=new_block)

    assert created.id == new_block.id
    refreshed = client.notebooks.get_by_id(id=seeded_notebook.id)
    assert existing_ids | {created.id} <= {b.id for b in refreshed.blocks}


def test_create_block_after_a_given_block(client: Albert, seeded_notebook: Notebook):
    """Test creating a block with previous_block_id places it directly after that block."""
    anchor = seeded_notebook.blocks[0]
    new_block = ParagraphBlock(content=ParagraphContent(text="Placed after the first block."))

    created = client.notebooks.create_block(
        notebook_id=seeded_notebook.id, block=new_block, previous_block_id=anchor.id
    )

    refreshed_ids = [b.id for b in client.notebooks.get_by_id(id=seeded_notebook.id).blocks]
    assert refreshed_ids.index(created.id) == refreshed_ids.index(anchor.id) + 1


def test_update_block(client: Albert, seeded_notebook: Notebook):
    """Test updating a block changes its content in place and leaves other blocks untouched."""
    paragraph = next(b for b in seeded_notebook.blocks if isinstance(b, ParagraphBlock))
    updated_block = paragraph.model_copy(deep=True)
    updated_block.content.text = "Updated in place."

    result = client.notebooks.update_block(notebook_id=seeded_notebook.id, block=updated_block)

    assert result.id == paragraph.id
    assert result.content.text == "Updated in place."
    refreshed = client.notebooks.get_by_id(id=seeded_notebook.id)
    assert [b.id for b in refreshed.blocks] == [b.id for b in seeded_notebook.blocks]


def test_delete_block(client: Albert, seeded_notebook: Notebook):
    """Test deleting a block removes it from the notebook."""
    block = client.notebooks.create_block(
        notebook_id=seeded_notebook.id,
        block=ParagraphBlock(content=ParagraphContent(text="Delete me.")),
    )

    client.notebooks.delete_block(notebook_id=seeded_notebook.id, block_id=block.id)

    refreshed = client.notebooks.get_by_id(id=seeded_notebook.id)
    assert block.id not in {b.id for b in refreshed.blocks}


def test_get_versions_and_restore_version(client: Albert, seeded_notebook: Notebook):
    """Test saved versions of a notebook can be listed and restored."""
    versions = poll_until(lambda: client.notebooks.get_versions(notebook_id=seeded_notebook.id))
    assert versions, "Expected at least one saved version after content edits"
    assert all(version.id for version in versions)

    restored = client.notebooks.restore_version(
        notebook_id=seeded_notebook.id, version_id=versions[0].id
    )

    assert restored.id == seeded_notebook.id
    assert len(restored.blocks) > 0
