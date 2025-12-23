from pydantic import TypeAdapter, validate_call

from albert.collections.base import BaseCollection
from albert.collections.synthesis import SynthesisCollection
from albert.core.base import BaseAlbertModel
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import NotebookId, ProjectId, SynthesisId, TaskId
from albert.exceptions import AlbertException
from albert.resources.notebooks import (
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
    """NotebookCollection is a collection class for managing Notebook entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the NotebookCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{NotebookCollection._api_version}/notebooks"
        self._synthesis = SynthesisCollection(session=session)

    @validate_call
    def get_by_id(self, *, id: NotebookId) -> Notebook:
        """Retrieve a Notebook by its ID.

        Parameters
        ----------
        id : str
            The ID of the Notebook to retrieve.

        Returns
        -------
        Notebook
            The Notebook object.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Notebook(**response.json())

    @validate_call
    def list_by_parent_id(self, *, parent_id: ProjectId | TaskId) -> list[Notebook]:
        """Retrieve a Notebook by parent ID.

        Parameters
        ----------
        parent_id : str
            The ID of the parent ID, e.g. task or project.

        Returns
        -------
        list[Notebook]
            list of notebook references.

        """

        # search
        response = self.session.get(f"{self.base_path}/{parent_id}/search")
        # return
        return [self.get_by_id(id=x["id"]) for x in response.json()["Items"]]

    def create(self, *, notebook: Notebook) -> Notebook:
        """Create or return notebook for the provided notebook.
        This endpoint automatically tries to find an existing notebook with the same parameter setpoints, and will either return the existing notebook or create a new one.

        Parameters
        ----------
        notebook : Notebook
            A list of Notebook entities to find or create.

        Returns
        -------
        Notebook
            A list of created or found Notebook entities.
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
        """
        Deletes a notebook by its ID.

        Parameters
        ----------
        id : str
            The ID of the notebook to delete.
        """
        self.session.delete(f"{self.base_path}/{id}")

    def update(self, *, notebook: Notebook) -> Notebook:
        """Update a notebook.

        Parameters
        ----------
        notebook : Notebook
            The updated notebook object.

        Returns
        -------
        Notebook
            The updated notebook object as returned by the server.
        """
        existing_notebook = self.get_by_id(id=notebook.id)
        patch_data = self._generate_patch_payload(existing=existing_notebook, updated=notebook)
        url = f"{self.base_path}/{notebook.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=notebook.id)

    def update_block_content(self, *, notebook: Notebook) -> Notebook:
        """
        Updates the block content of a Notebook. This does not update the notebook name (use .update for that).
        If a block in the Notebook does not already exist on Albert, it will be created.
        *Note: The order of the Blocks in your Notebook matter and will be used in the updated Notebook!*


        Parameters
        ----------
        notebook : Notebook
            The updated notebook object.

        Returns
        -------
        Notebook
            The updated notebook object as returned by the server.

        Examples
        --------
        !!! example "Add a Ketcher block from SMILES"
            ```python
            notebook = client.notebooks.get_by_id(id="NTB123")
            notebook.blocks.append(
                KetcherBlock(content=KetcherContent(smiles="CCO"))
            )
            notebook = client.notebooks.update_block_content(notebook=notebook)
            ```
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
    def get_block_by_id(self, *, notebook_id: NotebookId, block_id: str) -> NotebookBlock:
        """Retrieve a Notebook Block by its ID.

        Parameters
        ----------
        notebook_id : str
            The ID of the Notebook to which the Block belongs.
        block_id : str
            The ID of the Notebook Block to retrieve.

        Returns
        -------
        NotebookBlock
            The NotebookBlock object.
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

            if isinstance(block, KetcherBlock):
                ketcher_updates.append(self._prepare_ketcher_block(notebook=notebook, block=block))

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

    def _prepare_ketcher_block(
        self, *, notebook: Notebook, block: KetcherBlock
    ) -> _KetcherUpdateAction:
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
        """Create a copy of a Notebook into a specified parent

        Parameters
        ----------
        notebook_copy_info : NotebookCopyInfo
            The copy information for the Notebook copy
        type : NotebookCopyType
            Differentiate whether copy is for templates, task, project or restoreTemplate

        Returns
        -------
        Notebook
            The result of the copied Notebook.
        """
        response = self.session.post(
            url=f"{self.base_path}/copy",
            json=notebook_copy_info.model_dump(mode="json", by_alias=True, exclude_none=True),
            params={"type": type, "parentId": notebook_copy_info.parent_id},
        )
        return Notebook(**response.json())
