import mimetypes
from pathlib import Path, PurePosixPath

from pydantic import TypeAdapter, validate_call

from albert.collections.base import BaseCollection
from albert.collections.files import FileCollection
from albert.collections.synthesis import SynthesisCollection
from albert.core.base import BaseAlbertModel
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import NotebookId, ProjectId, SynthesisId, TaskId
from albert.exceptions import AlbertException
from albert.resources.files import FileNamespace
from albert.resources.notebooks import (
    AttachesBlock,
    ImageBlock,
    KetcherBlock,
    Notebook,
    NotebookBlock,
    NotebookCopyInfo,
    NotebookCopyType,
    PutBlockDatum,
    PutBlockPayload,
    PutOperation,
)


class _KetcherUpdateAction(BaseAlbertModel):
    synthesis_id: SynthesisId
    data: str
    png: str
    smiles: str


class NotebookCollection(BaseCollection):
    """Manage Notebooks in the Albert platform.

    A Notebook is an electronic lab notebook (ELN): an ordered document made up
    of content blocks (paragraphs, headers, checklists, tables, images, file
    attachments, and Ketcher chemical drawings). Each Notebook is attached to a
    parent entity, which is a Project, a Task, or a custom template, and is
    referenced by its Notebook ID (format ``NTB...``, e.g. ``"NTB123"``).

    Notebook content is edited block-by-block rather than by overwriting the whole
    document. Create an empty Notebook with [`create`][albert.collections.notebooks.NotebookCollection.create], then add or change
    blocks with [`update_block_content`][albert.collections.notebooks.NotebookCollection.update_block_content] or [`append_blocks`][albert.collections.notebooks.NotebookCollection.append_blocks]. The
    [`update`][albert.collections.notebooks.NotebookCollection.update] method changes only the Notebook name.

    This collection is accessed as ``client.notebooks``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        notebook = client.notebooks.get_by_id(id="NTB123")
        for block in notebook.blocks:
            print(block.id, block.type)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for notebook requests.

    Methods
    -------
    get_by_id(id) -> Notebook
        Get a single notebook by its ID.
    list_by_parent_id(parent_id) -> list[Notebook]
        List the notebooks attached to a given parent (project or task).
    create(notebook) -> Notebook
        Find or create an (empty) notebook for the given parent.
    delete(id) -> None
        Delete a notebook by its ID.
    update(notebook) -> Notebook
        Update a notebook's name.
    update_block_content(notebook) -> Notebook
        Replace the notebook's block content with the blocks on the object.
    append_blocks(id, blocks) -> Notebook
        Append blocks to the end of a notebook, preserving existing blocks.
    get_block_by_id(notebook_id, block_id) -> NotebookBlock
        Get a single block from a notebook by block ID.
    copy(notebook_copy_info, type) -> Notebook
        Copy a notebook into a specified parent.
    """

    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a NotebookCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{NotebookCollection._api_version}/notebooks"
        self._files = FileCollection(session=session)
        self._synthesis = SynthesisCollection(session=session)

    @validate_call
    def get_by_id(self, *, id: NotebookId) -> Notebook:
        """Get a single Notebook by its ID.

        !!! example
            ```python
            notebook = client.notebooks.get_by_id(id="NTB123")
            print(notebook.name)
            ```

        Parameters
        ----------
        id : NotebookId
            The Notebook ID to retrieve (format ``NTB...``).

        Returns
        -------
        Notebook
            The fully populated notebook.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Notebook(**response.json())

    @validate_call
    def list_by_parent_id(self, *, parent_id: ProjectId | TaskId) -> list[Notebook]:
        """List the Notebooks attached to a given parent entity.

        !!! example
            ```python
            notebooks = client.notebooks.list_by_parent_id(parent_id="PRO123")
            for notebook in notebooks:
                print(notebook.id, notebook.name)
            ```

        Parameters
        ----------
        parent_id : ProjectId or TaskId
            The ID of the parent entity whose notebooks should be listed
            (a Project ID, format ``PRO...``, or a Task ID, format ``TAS...``).

        Returns
        -------
        list[Notebook]
            The fully populated notebooks attached to the parent.
        """

        # search
        response = self.session.get(f"{self.base_path}/{parent_id}/search")
        # return
        return [self.get_by_id(id=x["id"]) for x in response.json()["Items"]]

    def create(self, *, notebook: Notebook) -> Notebook:
        """Find or create a Notebook for the provided notebook.

        The endpoint first tries to find an existing notebook for the same parent
        with matching properties; if one is found it is returned, otherwise a new
        notebook is created.

        The notebook must be created empty: the ``blocks`` field must be empty.
        Add content afterward with [`update_block_content`][albert.collections.notebooks.NotebookCollection.update_block_content] or
        [`append_blocks`][albert.collections.notebooks.NotebookCollection.append_blocks].

        !!! example
            ```python
            from albert.resources.notebooks import Notebook

            notebook = client.notebooks.create(
                notebook=Notebook(name="Trial 1 log", parent_id="PRO123")
            )
            ```

        Parameters
        ----------
        notebook : Notebook
            The notebook to find or create. Must have a ``parent_id`` and no
            pre-filled ``blocks``.

        Returns
        -------
        Notebook
            The found or newly created notebook.

        Raises
        ------
        AlbertException
            If the notebook has pre-filled blocks.
        """
        if notebook.blocks:
            # This check keeps a user from corrupting the Notebook data.
            msg = (
                "Cannot create a Notebook with pre-filled blocks. "
                "Set `blocks=[]` (or do not set it) when creating it. "
                "Use `.update_block_content()` afterward to add, update, or delete blocks."
            )
            raise AlbertException(msg)
        response = self.session.post(
            url=self.base_path,
            json=notebook.model_dump(mode="json", by_alias=True, exclude_none=True),
            params={"parentId": notebook.parent_id},
        )
        return Notebook(**response.json())

    @validate_call
    def delete(self, *, id: NotebookId) -> None:
        """Delete a Notebook by its ID.

        !!! example
            ```python
            client.notebooks.delete(id="NTB123")
            ```

        Parameters
        ----------
        id : NotebookId
            The Notebook ID to delete (format ``NTB...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    def update(self, *, notebook: Notebook) -> Notebook:
        """Update a Notebook's name.

        This method changes only the notebook name; it does not modify block
        content. Use [`update_block_content`][albert.collections.notebooks.NotebookCollection.update_block_content] to change the blocks.

        !!! example
            ```python
            notebook = client.notebooks.get_by_id(id="NTB123")
            notebook.name = "Revised trial log"
            notebook = client.notebooks.update(notebook=notebook)
            ```

        Parameters
        ----------
        notebook : Notebook
            The notebook carrying the desired name. It must have an ``id``.

        Returns
        -------
        Notebook
            The updated notebook.

        Notes
        -----
        The following fields can be updated: ``name``.
        """
        existing_notebook = self.get_by_id(id=notebook.id)
        patch_data = self._generate_patch_payload(existing=existing_notebook, updated=notebook)
        url = f"{self.base_path}/{notebook.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=notebook.id)

    def update_block_content(self, *, notebook: Notebook) -> Notebook:
        """Replace a Notebook's block content with the blocks on the object.

        The notebook's ``blocks`` list is treated as the desired final state: the
        order of the blocks is preserved, any block not already on Albert is
        created, and any existing block that is no longer present is deleted. This
        does not change the notebook name (use [`update`][albert.collections.notebooks.NotebookCollection.update] for that).

        !!! warning
            Updating existing Ketcher blocks is not supported. To change a Ketcher
            block, delete it and create a new one instead.

        !!! example
            ```python
            # Add a Ketcher block from SMILES
            from albert.resources.notebooks import KetcherBlock, KetcherContent

            notebook = client.notebooks.get_by_id(id="NTB123")
            notebook.blocks.append(
                KetcherBlock(content=KetcherContent(smiles="CCO"))
            )
            notebook = client.notebooks.update_block_content(notebook=notebook)
            ```

        Parameters
        ----------
        notebook : Notebook
            The notebook whose ``blocks`` describe the desired content. It must
            have an ``id``.

        Returns
        -------
        Notebook
            The updated notebook.

        Raises
        ------
        AlbertException
            If the notebook has no ``id``, if two blocks share the same id, or if
            an existing block's type is changed in place.
        """
        if notebook.id is None:
            raise AlbertException("Notebook id is required to update block content.")
        put_data, ketcher_updates = self._generate_put_block_payload(notebook=notebook)
        url = f"{self.base_path}/{notebook.id}/content"

        self.session.put(url, json=put_data.model_dump(mode="json", by_alias=True))

        for action in ketcher_updates:
            self._synthesis.update_canvas_data(
                synthesis_id=action.synthesis_id,
                smiles=action.smiles,
                data=action.data,
                png=action.png,
            )
            self._synthesis.create_reactant_productant_table(synthesis_id=action.synthesis_id)
        return self.get_by_id(id=notebook.id)

    @validate_call
    def append_blocks(self, *, id: NotebookId, blocks: list[NotebookBlock]) -> Notebook:
        """Append blocks to the end of a Notebook, preserving existing blocks.

        This is a convenience wrapper around [`update_block_content`][albert.collections.notebooks.NotebookCollection.update_block_content]: it
        fetches the current notebook, adds the given blocks after the existing
        ones, and saves.

        !!! example
            ```python
            # Append a paragraph block
            from albert.resources.notebooks import ParagraphBlock, ParagraphContent

            notebook = client.notebooks.append_blocks(
                id="NTB123",
                blocks=[ParagraphBlock(content=ParagraphContent(text="Hello"))],
            )
            ```

        Parameters
        ----------
        id : NotebookId
            The Notebook ID to append to (format ``NTB...``).
        blocks : list[NotebookBlock]
            The blocks to append to the end of the notebook.

        Returns
        -------
        Notebook
            The updated notebook.
        """
        notebook = self.get_by_id(id=id)
        notebook.blocks.extend(blocks)
        return self.update_block_content(notebook=notebook)

    @validate_call
    def get_block_by_id(self, *, notebook_id: NotebookId, block_id: str) -> NotebookBlock:
        """Get a single block from a Notebook by block ID.

        !!! example
            ```python
            block = client.notebooks.get_block_by_id(
                notebook_id="NTB123", block_id="abc-123"
            )
            ```

        Parameters
        ----------
        notebook_id : NotebookId
            The Notebook ID the block belongs to (format ``NTB...``).
        block_id : str
            The ID of the block to retrieve.

        Returns
        -------
        NotebookBlock
            The requested block, typed according to its block type (e.g.
            [`ParagraphBlock`][albert.resources.notebooks.ParagraphBlock]).
        """
        response = self.session.get(f"{self.base_path}/{notebook_id}/blocks/{block_id}")
        return TypeAdapter(NotebookBlock).validate_python(response.json())

    def _generate_put_block_payload(
        self, *, notebook: Notebook
    ) -> tuple[PutBlockPayload, list[_KetcherUpdateAction]]:
        data: list[PutBlockDatum] = []
        seen_ids: set[str] = set()
        previous_block_id = ""
        ketcher_updates: list[_KetcherUpdateAction] = []
        existing_blocks = {b.id: b for b in self.get_by_id(id=notebook.id).blocks}
        for block in notebook.blocks:
            if block.id in seen_ids:
                msg = f"You have Notebook blocks with duplicate ids. [id={block.id}]"
                raise AlbertException(msg)
            existing_block = existing_blocks.get(block.id)
            if existing_block and type(block) is not type(existing_block):
                msg = (
                    f"Cannot convert an existing block type into another block type. "
                    f"Instead, please instantiate a new block, and remove the old block "
                    f"from the Notebook object. [existing_block_type={type(existing_block)}, "
                    f"new_block_type={type(block)}]"
                )
                raise AlbertException(msg)

            if isinstance(block, KetcherBlock) and existing_block is None:
                ketcher_updates.append(self._prepare_ketcher_block(notebook=notebook, block=block))
            elif isinstance(block, (AttachesBlock | ImageBlock)):
                self._prepare_file_block(notebook=notebook, block=block)

            put_datum = PutBlockDatum(
                id=block.id,
                type=block.type,
                content=block.content,
                operation=PutOperation.UPDATE,
                previous_block_id=previous_block_id,
            )
            seen_ids.add(put_datum.id)
            previous_block_id = put_datum.id
            data.append(put_datum)

        for block in existing_blocks.values():
            if block.id not in seen_ids:
                data.append(PutBlockDatum(id=block.id, operation=PutOperation.DELETE))

        return PutBlockPayload(data=data), ketcher_updates

    def _prepare_file_block(
        self, *, notebook: Notebook, block: AttachesBlock | ImageBlock
    ) -> None:
        content = block.content
        file_path = content.file_path
        file_key = content.file_key
        if file_path is None:
            if file_key:
                file_name = PurePosixPath(file_key).name
                if "/" not in file_key:
                    content.file_key = f"{notebook.id}/{block.id}/{file_key}"
                if content.format is None:
                    content.format = (
                        mimetypes.guess_type(file_name)[0] or "application/octet-stream"
                    )
                if isinstance(block, AttachesBlock) and content.title is None:
                    content.title = file_name or None
            return

        path = Path(file_path)
        if file_key and "/" not in file_key:
            file_key = f"{notebook.id}/{block.id}/{file_key}"
        elif not file_key:
            file_key = f"{notebook.id}/{block.id}/{path.name}"

        content.file_key = file_key
        file_name = PurePosixPath(file_key).name
        if content.format is None:
            content.format = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        if isinstance(block, AttachesBlock) and content.title is None:
            content.title = file_name or None

        with path.open("rb") as handle:
            self._files.sign_and_upload_file(
                data=handle,
                name=file_key,
                namespace=FileNamespace(content.namespace),
                content_type=content.format,
            )

    def _prepare_ketcher_block(
        self, *, notebook: Notebook, block: KetcherBlock
    ) -> _KetcherUpdateAction:
        """
        Prepare a Ketcher block for creation.

        Updates to existing Ketcher blocks are not supported. To change a Ketcher
        block, delete it and create a new one instead.
        """
        content = block.content
        smiles = content.smiles or ""
        data = content.data
        png = content.png

        if content.synthesis_id is None:
            if not smiles:
                raise AlbertException("smiles is required to create a Ketcher block.")
            name = "Chemical Draw Block"
            synthesis = self._synthesis.create(
                parent_id=notebook.id, name=name, block_id=block.id, smiles=smiles or None
            )
            content.synthesis_id = synthesis.id
            content.s3_key = synthesis.s3_key or content.s3_key

            canvas_data = synthesis.canvas_data or {}
            data = data or canvas_data.get("data")
            png = png or canvas_data.get("png")

        content.id = block.id
        content.block_id = block.id
        content.state_type = "project"
        content.smiles = smiles
        content.data = data
        content.png = png

        return _KetcherUpdateAction(
            synthesis_id=content.synthesis_id,
            data=data or "",
            png=png or "",
            smiles=smiles or "",
        )

    def copy(self, *, notebook_copy_info: NotebookCopyInfo, type: NotebookCopyType) -> Notebook:
        """Copy a Notebook into a specified parent.

        !!! example
            ```python
            from albert.resources.notebooks import NotebookCopyInfo, NotebookCopyType

            copy = client.notebooks.copy(
                notebook_copy_info=NotebookCopyInfo(id="NTB123", parent_id="PRO456"),
                type=NotebookCopyType.PROJECT,
            )
            ```

        Parameters
        ----------
        notebook_copy_info : NotebookCopyInfo
            Describes the source notebook and the destination parent for the copy.
        type : NotebookCopyType
            The kind of copy to perform (e.g. into a template, task, or project,
            or restoring a template).

        Returns
        -------
        Notebook
            The newly created copy.
        """
        response = self.session.post(
            url=f"{self.base_path}/copy",
            json=notebook_copy_info.model_dump(mode="json", by_alias=True, exclude_none=True),
            params={"type": type, "parentId": notebook_copy_info.parent_id},
        )
        return Notebook(**response.json())
