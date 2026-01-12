# Notebooks

Notebooks in Albert Invent are a tool for organizing your laboratory work in a centralized, secure place that is connected to other parts of the Albert platform. They allow you to capture unstructured notes and data, attachments, images, and documents within Projects, set up complex synthesis instructions, document Standard Operating Procedures (SOPs), and collaborate with team members.

## Create a notebook

!!! example "Create an empty notebook"
    ```python
    from albert import Albert
    from albert.resources.notebooks import Notebook

    client = Albert.from_client_credentials()

    notebook = Notebook(parent_id="PRJ123", name="Reaction Notes")
    notebook = client.notebooks.create(notebook=notebook)
    ```

## Add different block types

!!! example "Add header, paragraph, checklist, table, image, and attachment blocks"
    ```python
    from pathlib import Path

    from albert import Albert
    from albert.resources.notebooks import (
        AttachesBlock,
        AttachesContent,
        ChecklistBlock,
        ChecklistContent,
        ChecklistItem,
        HeaderBlock,
        HeaderContent,
        ImageBlock,
        ImageContent,
        ParagraphBlock,
        ParagraphContent,
        TableBlock,
        TableContent,
    )

    client = Albert.from_client_credentials()

    notebook = client.notebooks.get_by_id(id="NTB123")

    # Provide a file path to upload for image and attachment blocks.
    image_path = Path("/path/to/image.png")
    image_block = ImageBlock(content=ImageContent(file_path=image_path, with_background=True))
    attaches_block = AttachesBlock(content=AttachesContent(file_path=image_path))

    notebook.blocks = [
        HeaderBlock(content=HeaderContent(level=2, text="Notebook overview")),
        ParagraphBlock(content=ParagraphContent(text="Run conditions and observations.")),
        ChecklistBlock(
            content=ChecklistContent(
                items=[
                    ChecklistItem(checked=False, text="Prepare reagents"),
                    ChecklistItem(checked=True, text="Start reaction"),
                ]
            )
        ),
        TableBlock(
            content=TableContent(
                content=[
                    ["Reagent", "Mass (mg)"],
                    ["A", "10"],
                    ["B", "25"],
                ],
                with_headings=True,
            )
        ),
        image_block,
        attaches_block,
    ]

    notebook = client.notebooks.update_block_content(notebook=notebook)
    ```

!!! note
    When `file_path` is set on image or attachment content, the SDK uploads the file and fills in
    `file_key`, `format`, and (for attachments) `title`.

## Add a Ketcher block

!!! example "Create a new Ketcher block with SMILES"
    ```python
    from albert import Albert
    from albert.resources.notebooks import KetcherBlock, KetcherContent

    client = Albert.from_client_credentials()

    notebook = client.notebooks.get_by_id(id="NTB123")
    notebook.blocks.append(
        KetcherBlock(content=KetcherContent(smiles="CCO"))
    )
    notebook = client.notebooks.update_block_content(notebook=notebook)
    ```

!!! warning
    Updating existing Ketcher blocks is not supported. To change a Ketcher block, remove
    it from `notebook.blocks` and add a new Ketcher block with the desired `smiles`.

## Replace a Ketcher block

!!! example "Delete the old Ketcher block and add a new one"
    ```python
    from albert import Albert
    from albert.resources.notebooks import KetcherBlock, KetcherContent

    client = Albert.from_client_credentials()

    notebook = client.notebooks.get_by_id(id="NTB123")

    # Drop existing Ketcher blocks (this deletes them on update).
    notebook.blocks = [b for b in notebook.blocks if b.type != "ketcher"]

    # Add a new Ketcher block.
    notebook.blocks.append(
        KetcherBlock(content=KetcherContent(smiles="C1=CC=CC=C1"))
    )

    notebook = client.notebooks.update_block_content(notebook=notebook)
    ```

## Copy a notebook

!!! example "Copy a notebook to another parent"
    ```python
    from albert import Albert
    from albert.resources.notebooks import NotebookCopyInfo, NotebookCopyType

    client = Albert.from_client_credentials()

    copy_info = NotebookCopyInfo(id="NTB123", parent_id="PRJ456")
    notebook_copy = client.notebooks.copy(
        notebook_copy_info=copy_info,
        type=NotebookCopyType.PROJECT,
    )
    print(notebook_copy.id)
    ```
