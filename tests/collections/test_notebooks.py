from collections.abc import Iterator

import pytest

from albert import Albert
from albert.exceptions import AlbertException
from albert.resources.notebooks import (
    HeaderBlock,
    HeaderContent,
    KetcherBlock,
    KetcherContent,
    Notebook,
    NotebookCopyInfo,
    NotebookCopyType,
    ParagraphBlock,
    ParagraphContent,
)
from albert.resources.projects import Project
from albert.resources.synthesis import CanvasData, Synthesis
from tests.seeding import generate_notebook_block_seeds, generate_notebook_seeds


class StubSynthesisCollection:
    def __init__(self, created_id: str = "SYNSTUB"):
        self.created_calls: list[tuple[str, str, str]] = []
        self.updated_calls: list[tuple[str, str, CanvasData]] = []
        self.table_calls: list[str] = []
        self.created_id = created_id

    def create(self, *, parent_id: str, name: str, block_id: str) -> Synthesis:
        self.created_calls.append((parent_id, name, block_id))
        return Synthesis(albertId=self.created_id, parentId=parent_id, blockId=block_id)

    def update_canvas_data(
        self, *, synthesis_id: str, smiles: str, canvas_data: CanvasData
    ) -> Synthesis:
        self.updated_calls.append((synthesis_id, smiles, canvas_data))
        return Synthesis(
            albertId=synthesis_id,
            s3Key=f"TEN1/{synthesis_id}/ketcher.json",
        )

    def create_reactant_productant_table(self, *, synthesis_id: str) -> None:
        self.table_calls.append(synthesis_id)


@pytest.fixture(scope="function")
def seeded_notebook(
    client: Albert, seed_prefix: str, seeded_projects: Iterator[list[Project]]
) -> Iterator[Notebook]:
    notebook = generate_notebook_seeds(seed_prefix=seed_prefix, seeded_projects=seeded_projects)[0]
    seeded = client.notebooks.create(notebook=notebook)
    seeded.blocks = generate_notebook_block_seeds()
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


def test_update_block_content_with_empty_text(client: Albert, seeded_notebook: Notebook):
    # Ensure we can enter blocks with None Fields
    header_block = HeaderBlock(content=HeaderContent(level=1, text=None))
    seeded_notebook.blocks.append(header_block)
    updated_notebook = client.notebooks.update_block_content(notebook=seeded_notebook)
    assert updated_notebook.blocks[-1].content.text is None


def test_update_block_content_raises_exception(client: Albert, seeded_notebook: Notebook):
    # Try to change the type of a notebook block
    notebook = seeded_notebook.model_copy()
    header_block = HeaderBlock(content=HeaderContent(level=1, text="Header block"))
    notebook.blocks.append(header_block)
    notebook = client.notebooks.update_block_content(notebook=notebook)
    paragraph_content = ParagraphContent(text="HeaderBlock to ParagraphBlock")
    notebook.blocks[-1] = ParagraphBlock(id=header_block.id, content=paragraph_content)
    with pytest.raises(AlbertException, match="Cannot convert an existing block type"):
        client.notebooks.update_block_content(notebook=notebook)

    # Try to create notebook blocks with duplicate ids
    notebook = seeded_notebook.model_copy()
    header_block1 = HeaderBlock(content=HeaderContent(level=1, text="Header block 1"))
    header_block2 = HeaderBlock(
        id=header_block1.id, content=HeaderContent(level=1, text="Header block 2")
    )
    notebook.blocks.extend([header_block1, header_block2])
    with pytest.raises(AlbertException, match="You have Notebook blocks with duplicate ids"):
        client.notebooks.update_block_content(notebook=notebook)


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


def test_prepare_ketcher_blocks_creates_synthesis(fake_client: Albert):
    notebook_collection = fake_client.notebooks
    stub = StubSynthesisCollection(created_id="SYNNEW1")
    notebook_collection._synthesis = stub

    block = KetcherBlock(
        id="BLK1",
        content=KetcherContent(
            name="Chemical Draw Block",
            smiles="C1=CC=CC=C1",
            canvas_data=CanvasData(data="jsondump", png="bytes"),
        ),
    )
    notebook = Notebook(id="NTB12345", parent_id="PRJ12345", blocks=[block])

    notebook_collection._prepare_ketcher_blocks(notebook=notebook)

    assert block.content.synthesis_id == "SYNNEW1"
    assert block.content.s3_key == "TEN1/SYNNEW1/ketcher.json"
    assert stub.created_calls == [("NTB12345", "Chemical Draw Block", "BLK1")]
    assert stub.updated_calls[0][0] == "SYNNEW1"
    assert stub.table_calls == ["SYNNEW1"]


def test_prepare_ketcher_blocks_skips_when_no_canvas(fake_client: Albert):
    notebook_collection = fake_client.notebooks
    stub = StubSynthesisCollection()
    notebook_collection._synthesis = stub

    block = KetcherBlock(
        id="BLK2",
        content=KetcherContent(
            synthesis_id="SYNEXIST",
            s3_key="TEN1/SYNEXIST/ketcher.json",
        ),
    )
    notebook = Notebook(id="NTB54321", parent_id="PRJ54321", blocks=[block])

    notebook_collection._prepare_ketcher_blocks(notebook=notebook)

    assert not stub.created_calls
    assert not stub.updated_calls
    assert block.content.s3_key == "TEN1/SYNEXIST/ketcher.json"


def test_prepare_ketcher_blocks_updates_existing(fake_client: Albert):
    notebook_collection = fake_client.notebooks
    stub = StubSynthesisCollection()
    notebook_collection._synthesis = stub

    block = KetcherBlock(
        id="BLK3",
        content=KetcherContent(
            synthesis_id="SYN7777",
            s3_key="OLDKEY",
            smiles="C1CCCCC1",
            canvas_data=CanvasData(data="newjson", png="newbytes"),
        ),
    )
    notebook = Notebook(id="NTB77777", parent_id="PRJ77777", blocks=[block])

    notebook_collection._prepare_ketcher_blocks(notebook=notebook)

    assert not stub.created_calls
    assert stub.updated_calls[0][0] == "SYN7777"
    assert block.content.s3_key == "TEN1/SYN7777/ketcher.json"
    assert not stub.table_calls
