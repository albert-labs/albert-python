"""Unit tests for NotebookCollection private block-payload builders.

``tests/unit/resources/test_notebooks.py`` already covers the resource models
(``PutBlockDatum`` content/type validation, ``TableBlock.to_df``, ``ChecklistBlock``);
this file only exercises the collection's private, non-public helpers.
"""

from __future__ import annotations

import pytest
import responses

from albert.collections.notebooks import NotebookCollection
from albert.exceptions import AlbertException
from albert.resources.notebooks import (
    AttachesBlock,
    AttachesContent,
    HeaderBlock,
    HeaderContent,
    ImageBlock,
    ImageContent,
    KetcherBlock,
    KetcherContent,
    Notebook,
    NotebookBlock,
    ParagraphBlock,
    ParagraphContent,
    PutOperation,
)
from tests.unit.conftest import UNIT_BASE_URL


def _notebook_payload(*, notebook_id: str, blocks: list[NotebookBlock]) -> dict:
    """Build the JSON body ``get_by_id`` would return for a notebook with ``blocks``."""
    notebook = Notebook(id=notebook_id, parent_id="PRO1", blocks=blocks)
    return notebook.model_dump(by_alias=True, mode="json")


def _mock_get_by_id(*, notebook_id: str, blocks: list[NotebookBlock]) -> None:
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/notebooks/{notebook_id}",
        json=_notebook_payload(notebook_id=notebook_id, blocks=blocks),
    )


# ---------------------------------------------------------------------------
# _generate_put_block_payload
# ---------------------------------------------------------------------------


@responses.activate
def test_generate_put_block_payload_raises_on_duplicate_block_ids(offline_session):
    """Test that two blocks sharing an id raise before any payload is built."""
    collection = NotebookCollection(session=offline_session)
    _mock_get_by_id(notebook_id="NTB1", blocks=[])
    block = ParagraphBlock(id="B1", content=ParagraphContent(text="hi"))
    notebook = Notebook(id="NTB1", parent_id="PRO1", blocks=[block, block])

    with pytest.raises(AlbertException, match="duplicate ids"):
        collection._generate_put_block_payload(notebook=notebook)


@responses.activate
def test_generate_put_block_payload_raises_when_existing_block_changes_type(offline_session):
    """Test that reusing an existing block id with a different block type raises."""
    collection = NotebookCollection(session=offline_session)
    existing_block = ParagraphBlock(id="B1", content=ParagraphContent(text="old"))
    _mock_get_by_id(notebook_id="NTB1", blocks=[existing_block])
    new_block = HeaderBlock(id="B1", content=HeaderContent(level=1, text="new"))
    notebook = Notebook(id="NTB1", parent_id="PRO1", blocks=[new_block])

    with pytest.raises(AlbertException, match="Cannot convert an existing block type"):
        collection._generate_put_block_payload(notebook=notebook)


@responses.activate
def test_generate_put_block_payload_allows_same_id_when_type_unchanged(offline_session):
    """Test that reusing an existing block id with the same block type is allowed."""
    collection = NotebookCollection(session=offline_session)
    existing_block = ParagraphBlock(id="B1", content=ParagraphContent(text="old"))
    _mock_get_by_id(notebook_id="NTB1", blocks=[existing_block])
    updated_block = ParagraphBlock(id="B1", content=ParagraphContent(text="new"))
    notebook = Notebook(id="NTB1", parent_id="PRO1", blocks=[updated_block])

    payload, _ = collection._generate_put_block_payload(notebook=notebook)

    assert len(payload.data) == 1
    assert payload.data[0].id == "B1"
    assert payload.data[0].operation == PutOperation.UPDATE
    assert payload.data[0].content.text == "new"


@responses.activate
def test_generate_put_block_payload_chains_previous_block_id(offline_session):
    """Test that each block's previous_block_id points at the prior block, first is empty."""
    collection = NotebookCollection(session=offline_session)
    _mock_get_by_id(notebook_id="NTB1", blocks=[])
    b1 = ParagraphBlock(id="B1", content=ParagraphContent(text="first"))
    b2 = ParagraphBlock(id="B2", content=ParagraphContent(text="second"))
    notebook = Notebook(id="NTB1", parent_id="PRO1", blocks=[b1, b2])

    payload, ketcher_updates = collection._generate_put_block_payload(notebook=notebook)

    assert [d.id for d in payload.data] == ["B1", "B2"]
    assert payload.data[0].previous_block_id == ""
    assert payload.data[1].previous_block_id == "B1"
    assert ketcher_updates == []


@responses.activate
def test_generate_put_block_payload_deletes_blocks_removed_from_notebook(offline_session):
    """Test that a previously-existing block missing from the new list gets a DELETE op."""
    collection = NotebookCollection(session=offline_session)
    existing_block = ParagraphBlock(id="B1", content=ParagraphContent(text="old"))
    _mock_get_by_id(notebook_id="NTB1", blocks=[existing_block])
    kept_block = ParagraphBlock(id="B2", content=ParagraphContent(text="kept"))
    notebook = Notebook(id="NTB1", parent_id="PRO1", blocks=[kept_block])

    payload, _ = collection._generate_put_block_payload(notebook=notebook)

    ops = {d.id: d.operation for d in payload.data}
    assert ops["B2"] == PutOperation.UPDATE
    assert ops["B1"] == PutOperation.DELETE
    # A pure delete op carries no type/content.
    delete_datum = next(d for d in payload.data if d.id == "B1")
    assert delete_datum.type is None
    assert delete_datum.content is None


# ---------------------------------------------------------------------------
# _prepare_file_block
# ---------------------------------------------------------------------------


def test_prepare_file_block_builds_nested_key_and_infers_format_from_existing_key(offline_session):
    """Test that a bare file_key is namespaced under notebook/block and format is inferred."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = AttachesBlock(id="B1", content=AttachesContent(file_key="results.csv"))

    collection._prepare_file_block(notebook=notebook, block=block)

    assert block.content.file_key == "NTB1/B1/results.csv"
    assert block.content.format == "text/csv"
    assert block.content.title == "results.csv"


def test_prepare_file_block_keeps_already_nested_file_key(offline_session):
    """Test that a file_key already containing a '/' is left untouched, custom title kept."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = AttachesBlock(
        id="B1", content=AttachesContent(file_key="already/nested/key.csv", title="Custom")
    )

    collection._prepare_file_block(notebook=notebook, block=block)

    assert block.content.file_key == "already/nested/key.csv"
    assert block.content.title == "Custom"


def test_prepare_file_block_noop_when_no_file_path_or_key(offline_session):
    """Test that a block with neither file_path nor file_key is left unchanged."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = ImageBlock(id="B1", content=ImageContent())

    collection._prepare_file_block(notebook=notebook, block=block)

    assert block.content.file_key is None
    assert block.content.format is None


@responses.activate
def test_prepare_file_block_uploads_local_file_and_sets_key(offline_session, tmp_path):
    """Test that a local file_path is uploaded and the block's file_key/format/title are set."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    file_path = tmp_path / "spectrum.pdf"
    file_path.write_bytes(b"content")
    block = AttachesBlock(id="B1", content=AttachesContent(file_path=str(file_path)))

    responses.post(
        f"{UNIT_BASE_URL}/api/v3/files/sign",
        json=[{"URL": "https://upload.example.com/put"}],
    )
    responses.put("https://upload.example.com/put", status=200)

    collection._prepare_file_block(notebook=notebook, block=block)

    assert block.content.file_key == "NTB1/B1/spectrum.pdf"
    assert block.content.format == "application/pdf"
    assert block.content.title == "spectrum.pdf"
    assert len(responses.calls) == 2


@responses.activate
def test_prepare_file_block_uploads_with_caller_supplied_file_key(offline_session, tmp_path):
    """Test that a caller-supplied bare file_key alongside file_path is namespaced, not replaced."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    file_path = tmp_path / "spectrum.pdf"
    file_path.write_bytes(b"content")
    block = AttachesBlock(
        id="B1", content=AttachesContent(file_path=str(file_path), file_key="customkey.pdf")
    )

    responses.post(
        f"{UNIT_BASE_URL}/api/v3/files/sign",
        json=[{"URL": "https://upload.example.com/put"}],
    )
    responses.put("https://upload.example.com/put", status=200)

    collection._prepare_file_block(notebook=notebook, block=block)

    assert block.content.file_key == "NTB1/B1/customkey.pdf"
    assert block.content.title == "customkey.pdf"


# ---------------------------------------------------------------------------
# _prepare_ketcher_block
# ---------------------------------------------------------------------------


def test_prepare_ketcher_block_reuses_existing_synthesis_without_creating(offline_session):
    """Test that an existing synthesis_id skips creating a new synthesis record."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = KetcherBlock(
        id="B1",
        content=KetcherContent(synthesis_id="SYN1", smiles="CCO", data="rawdata", png="pngdata"),
    )

    # No responses registered: any HTTP call here would raise, proving no I/O occurs.
    action = collection._prepare_ketcher_block(notebook=notebook, block=block)

    assert action.synthesis_id == "SYN1"
    assert action.smiles == "CCO"
    assert action.data == "rawdata"
    assert action.png == "pngdata"
    assert block.content.id == "B1"
    assert block.content.block_id == "B1"
    assert block.content.state_type == "project"


def test_prepare_ketcher_block_raises_when_no_smiles_and_no_synthesis(offline_session):
    """Test that a new Ketcher block with no SMILES and no synthesis_id raises."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = KetcherBlock(id="B1", content=KetcherContent())

    with pytest.raises(AlbertException, match="smiles is required"):
        collection._prepare_ketcher_block(notebook=notebook, block=block)


@responses.activate
def test_prepare_ketcher_block_creates_synthesis_when_none_exists(offline_session):
    """Test that a new Ketcher block with a SMILES string creates a synthesis record."""
    collection = NotebookCollection(session=offline_session)
    notebook = Notebook(id="NTB1", parent_id="PRO1")
    block = KetcherBlock(id="B1", content=KetcherContent(smiles="CCO"))

    responses.post(
        f"{UNIT_BASE_URL}/api/v3/synthesis",
        json={
            "albertId": "SYN1",
            "s3Key": "s3/key",
            "canvasData": {"data": "canvas-data", "png": "canvas-png"},
        },
    )

    action = collection._prepare_ketcher_block(notebook=notebook, block=block)

    assert action.synthesis_id == "SYN1"
    assert action.data == "canvas-data"
    assert action.png == "canvas-png"
    assert block.content.synthesis_id == "SYN1"
    assert block.content.s3_key == "s3/key"
    assert block.content.smiles == "CCO"
