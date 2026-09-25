import pytest
from pandas import DataFrame

from albert.exceptions import AlbertException
from albert.resources.notebooks import (
    BlockType,
    ChecklistBlock,
    ChecklistContent,
    ChecklistItem,
    ParagraphContent,
    PutBlockDatum,
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
