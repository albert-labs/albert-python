import pytest
from pandas import DataFrame

from albert.exceptions import AlbertException
from albert.resources.acls import ACLContainer
from albert.resources.notebooks import (
    BlockType,
    ChecklistBlock,
    ChecklistContent,
    ChecklistItem,
    ExcelBlock,
    Notebook,
    NotebookCopyInfo,
    ParagraphContent,
    PowerPointBlock,
    PutBlockDatum,
    PutOperation,
    ReportBlock,
    TableBlock,
    TableContent,
    WordBlock,
)

pytestmark = pytest.mark.xdist_group("projects")


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


def test_notebook_parses_office_and_report_blocks():
    """Test notebooks containing Office and report blocks parse without error."""
    payload = {
        "albertId": "NTB123",
        "parentId": "PRO123",
        "blocks": [
            {
                "id": "b1",
                "blockType": "msdocx",
                "content": {"title": "Document1.docx", "fileKey": "NTB123/b1/Document1.docx"},
            },
            {
                "id": "b2",
                "blockType": "msxlsx",
                "content": {"title": "Book1.xlsx", "fileKey": "NTB123/b2/Book1.xlsx"},
            },
            {
                "id": "b3",
                "blockType": "mspptx",
                "content": {"title": "Powerpoint1.pptx", "fileKey": "NTB123/b3/Powerpoint1.pptx"},
            },
            {"id": "b4", "blockType": "report", "content": {"reportId": "REP123"}},
        ],
    }

    notebook = Notebook(**payload)

    assert isinstance(notebook.blocks[0], WordBlock)
    assert isinstance(notebook.blocks[1], ExcelBlock)
    assert isinstance(notebook.blocks[2], PowerPointBlock)
    assert isinstance(notebook.blocks[3], ReportBlock)
    assert notebook.blocks[0].content.file_key == "NTB123/b1/Document1.docx"
    # unknown report content keys are preserved
    assert notebook.blocks[3].content.model_dump()["reportId"] == "REP123"


def test_put_datum_accepts_office_and_report_content():
    """Test Office and report block contents pair with their block types."""
    for block in (WordBlock(), ExcelBlock(), PowerPointBlock(), ReportBlock()):
        datum = PutBlockDatum(
            id=block.id,
            type=block.type,
            content=block.content,
            operation=PutOperation.UPDATE,
        )
        assert datum.content is block.content


def test_copy_info_serializes_acl():
    """Test copy info sends access settings under the ``ACL`` wire key."""
    info = NotebookCopyInfo(
        id="NTB123",
        parent_id="PRO456",
        acl=ACLContainer(acl_class="restricted"),
    )

    payload = info.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert payload["ACL"] == {"class": "restricted"}
    assert "acl" not in payload


def test_copy_info_serializes_template_id():
    """Test copy info sends the source template under the ``templateId`` wire key."""
    info = NotebookCopyInfo(id="NTB123", parent_id="PRO456", template_id="CTP789")

    payload = info.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert payload["templateId"] == "CTP789"
