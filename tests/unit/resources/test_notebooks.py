import pytest
from pandas import DataFrame

from albert.exceptions import AlbertException
from albert.resources.notebooks import (
    BlockType,
    ChecklistBlock,
    ChecklistContent,
    ChecklistItem,
    NotebookCopyACL,
    ParagraphContent,
    PutBlockDatum,
    PutBlockPayload,
    PutOperation,
    TableBlock,
    TableContent,
)


def test_put_datum_content_matches_type():
    with pytest.raises(AlbertException, match="The content type and block type do not match."):
        PutBlockDatum(
            id="123",
            type=BlockType.KETCHER,
            content=ParagraphContent(text="test"),
            operation=PutOperation.UPDATE,
        )


def test_put_datum_content_matches_type_accepts_matching_content():
    """Test PutBlockDatum accepts content whose type matches the declared block type."""
    datum = PutBlockDatum(
        id="123",
        type=BlockType.PARAGRAPH,
        content=ParagraphContent(text="test"),
        operation=PutOperation.UPDATE,
    )
    assert datum.content.text == "test"


def test_put_datum_content_matches_type_skips_check_when_content_is_none():
    """Test PutBlockDatum skips the type check entirely when content is unset."""
    datum = PutBlockDatum(id="123", type=BlockType.PARAGRAPH, operation=PutOperation.DELETE)
    assert datum.content is None


def test_put_datum_content_matches_type_skips_check_when_type_unset():
    """Test PutBlockDatum skips the type check when no block type is declared."""
    datum = PutBlockDatum(
        id="123", content=ParagraphContent(text="test"), operation=PutOperation.UPDATE
    )
    assert datum.type is None
    assert datum.content.text == "test"


def test_put_datum_model_dump_drops_only_top_level_none_values():
    """Test PutBlockDatum.model_dump removes None only from the top level, not nested content."""
    datum = PutBlockDatum(
        id="123",
        type=BlockType.PARAGRAPH,
        content=ParagraphContent(text=None),
        operation=PutOperation.UPDATE,
    )
    dumped = datum.model_dump()
    assert "previous_block_id" not in dumped
    assert dumped["content"]["text"] is None


def test_put_block_payload_model_dump_delegates_per_item():
    """Test PutBlockPayload.model_dump dumps each datum with top-level None values stripped."""
    payload = PutBlockPayload(
        data=[
            PutBlockDatum(id="1", type=BlockType.PARAGRAPH, operation=PutOperation.DELETE),
            PutBlockDatum(
                id="2",
                type=BlockType.PARAGRAPH,
                content=ParagraphContent(text="hi"),
                operation=PutOperation.UPDATE,
            ),
        ]
    )
    dumped = payload.model_dump()
    assert "previous_block_id" not in dumped["data"][0]
    assert "content" not in dumped["data"][0]
    assert dumped["data"][1]["content"]["text"] == "hi"


def test_notebook_copy_acl_warns_on_construction():
    """Test NotebookCopyACL emits a DeprecationWarning when instantiated."""
    with pytest.warns(DeprecationWarning, match="NotebookCopyACL is deprecated"):
        NotebookCopyACL(**{"class": "restricted", "fgclist": []})


def test_table_block_to_df():
    # create table block
    table = TableBlock(
        content=TableContent(
            content=[
                ["H1", "H2", "H3"],
                ["row2-col1", "row2-col2", "row2-col3"],
                ["row3-col1", "row3-col2", "row3-col3"],
            ]
        )
    )
    # check table cobversion
    assert (table.to_df(infer_header=False) == DataFrame(table.content.content)).all().all()


def test_table_block_to_df_infers_header_by_default():
    """Test TableBlock.to_df strips HTML from the header row and uses it as columns."""
    table = TableBlock(
        content=TableContent(
            content=[
                ["<b>Trial</b>", "Yield"],
                ["1", "82%"],
                ["2", "91%"],
            ]
        )
    )
    df = table.to_df()
    assert list(df.columns) == ["Trial", "Yield"]
    assert list(df.iloc[0]) == ["1", "82%"]
    assert len(df) == 2


def test_checklist_block_is_checked():
    # create checklist block
    check_list_block = ChecklistBlock(
        content=ChecklistContent(
            items=[
                ChecklistItem(checked=True, text="I am checked."),
                ChecklistItem(checked=False, text="I am not checked."),
                ChecklistItem(checked=True, text="I am also checked."),
            ]
        )
    )
    # checks
    for i in check_list_block.content.items:
        assert i.checked == check_list_block.is_checked(target_text=i.text)


def test_checklist_block_is_checked_returns_none_for_missing_text():
    """Test ChecklistBlock.is_checked returns None when no item matches the given text."""
    check_list_block = ChecklistBlock(
        content=ChecklistContent(items=[ChecklistItem(checked=True, text="Calibrate scale")])
    )
    assert check_list_block.is_checked(target_text="Does not exist") is None
