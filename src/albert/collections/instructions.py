from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import InventoryId
from albert.resources.instructions import (
    BatchInstructions,
    Instruction,
    InstructionCopyResult,
    InstructionLayout,
    InstructionOrder,
    InstructionSequence,
    InstructionSet,
    SequencePosition,
)


class InventoryInstructionsMixin(BaseCollection):
    """Manage the batching instructions of formulas in the Albert platform.

    Batching instructions describe the procedure for making one specific formula
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]) as a batch:
    what you see on the formula's Instructions panel in the Albert interface.
    Two layers make it up:

    - **Instruction texts** ([`Instruction`][albert.resources.instructions.Instruction]):
      authored steps and notes, such as "Take the pH of the batch". Every
      instruction belongs to exactly one formula. An instruction can optionally
      be pinned to one of the formula's ingredient rows; without a pin it is a
      formula-level instruction. Instructions are added, renamed, reordered
      within their row, copied between formulas, and deleted through these
      methods.
    - **The procedure table** ([`BatchInstructions`][albert.resources.instructions.BatchInstructions]
      and [`InstructionRow`][albert.resources.instructions.InstructionRow]):
      the formula's ingredient rows, procedure stages such as "Premix" or
      "Heating", and readings from its Worksheet, which give the instructions
      their structure. Row content is edited on the Worksheet; rows are read
      through
      [`get_batch_instructions`][albert.collections.instructions.InventoryInstructionsMixin.get_batch_instructions].

    The row order and the instruction-text order are determined as follows:

    - Ingredient rows always follow the order set on the Sheet's Product Design;
      they cannot be reordered per formula.
    - Procedure stage rows default to the Sheet's Process Design order, but each
      formula can override the order of its own stages with
      [`move_procedure_stage`][albert.collections.instructions.InventoryInstructionsMixin.move_procedure_stage],
      placing a stage above or below any other row (ingredient or stage). A
      stage stays with the ingredient it follows, so reordering ingredients on
      the Sheet carries the formula's stages along; stages newly added to the
      Sheet are appended at the end.
    - Reading rows (the readings and targets inside a stage, such as
      temperature or mixing time) belong to their parent stage and move with
      it; they are not individually reorderable.
    - Instruction texts order independently of the rows: each ingredient row
      has its own order for the instructions pinned to it, plus one order for
      the formula-level instructions. New instructions are appended at the end
      of their order by default; reorder them with
      [`set_instruction_order`][albert.collections.instructions.InventoryInstructionsMixin.set_instruction_order].
      When instructions are read for a formula, the formula-level instructions
      come first, then each row's instructions.

    Moving stages with
    [`move_procedure_stage`][albert.collections.instructions.InventoryInstructionsMixin.move_procedure_stage]
    uses unique row IDs (format ``DES...#ROW...``), which are not the names or
    IDs users usually have in hand. To find them, read the formula's batching
    instructions with
    [`get_batch_instructions`][albert.collections.instructions.InventoryInstructionsMixin.get_batch_instructions]
    and match rows by their display ``name`` or by the entity behind the row
    (``id`` holds the parameter group ID or the ingredient's inventory ID); each
    row's ``row_unique_id`` is the value to pass when moving.

    These methods are mixed into the inventory collection, so they are available
    directly on ``client.inventory`` (for example
    ``client.inventory.get_batch_instructions``) and, identically, on the nested
    instructions collection at ``client.inventory.instructions``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        batch = client.inventory.get_batch_instructions(id="INV123")
        for instruction in batch.instructions:
            print(instruction.id, instruction.name)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Methods
    -------
    get_batch_instructions(id) -> BatchInstructions
        Get a formula's procedure rows, authored instruction texts, and row-order version.
    add_instruction(id, text, design_row_id) -> Instruction
        Add an instruction to a formula.
    rename_instruction(id, instruction_id, text) -> Instruction
        Rename an instruction on a formula.
    delete_instruction(id, instruction_id) -> None
        Delete an instruction from a formula.
    set_instruction_order(id, instruction_ids, design_row_id) -> InstructionSet
        Reorder the instructions within one row of a formula.
    copy_instructions(id, target_ids) -> InstructionCopyResult
        Copy a formula's instructions and their order to other formulas.
    move_procedure_stage(id, stage_row_id, reference_row_id, position, version) -> InstructionSequence
        Move a procedure stage row to a new position in the row order.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize an InventoryInstructionsMixin.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self._instructions_base_path = f"/api/{self._api_version}/instructions"
        self._inventory_base_path = f"/api/{self._api_version}/inventories"

    @staticmethod
    def _build_create_payload(*, id: str, text: str, design_row_id: str | None) -> dict:
        if not text:
            raise ValueError("text is required.")
        design_payload: dict[str, str] = {"productId": id}
        if design_row_id:
            design_payload["designRowId"] = design_row_id
        return {"name": text, "parentId": id, "Design": design_payload}

    @staticmethod
    def _build_rename_patch(*, instruction_id: str, old_text: str, new_text: str) -> dict | None:
        if new_text == old_text:
            return None
        return {
            "id": instruction_id,
            "data": [
                {
                    "operation": "update",
                    "attribute": "name",
                    "oldValue": old_text,
                    "newValue": new_text,
                }
            ],
        }

    @staticmethod
    def _build_instruction_order_payload(
        *,
        sequence: list[InstructionOrder],
        design_row_id: str | None,
        instruction_ids: list[str],
    ) -> dict:
        bucket = next(
            (bucket for bucket in sequence if bucket.design_row_id == design_row_id), None
        )
        if bucket is None:
            target = design_row_id if design_row_id is not None else "the formula level"
            raise ValueError(f"No instructions found for {target}.")
        current_ids = bucket.instruction_ids
        if sorted(current_ids) != sorted(instruction_ids):
            raise ValueError(
                "instruction_ids must contain exactly the IDs currently in the row, "
                "in the new order."
            )
        old_bucket: dict = {"rowSequence": current_ids}
        new_bucket: dict = {"rowSequence": instruction_ids}
        if design_row_id is not None:
            old_bucket["designRowId"] = design_row_id
            new_bucket["designRowId"] = design_row_id
        return {
            "data": [
                {
                    "operation": "update",
                    "attribute": "sequence",
                    "oldValue": [old_bucket],
                    "newValue": [new_bucket],
                }
            ]
        }

    @staticmethod
    def _build_stage_move_payload(
        *, stage_row_id: str, reference_row_id: str, position: SequencePosition, version: int
    ) -> dict:
        return {
            "data": [
                {
                    "operation": "update",
                    "attribute": "sequence",
                    "sourceId": stage_row_id,
                    "referenceId": reference_row_id,
                    "position": position.value,
                    "version": version,
                }
            ]
        }

    def _get_instruction_layout(self, *, id: InventoryId) -> InstructionLayout:
        response = self.session.get(f"{self._inventory_base_path}/{id}/instructions")
        return InstructionLayout(**response.json())

    def _get_instruction_sequence(self, *, id: InventoryId) -> InstructionSequence:
        response = self.session.get(
            f"{self._inventory_base_path}/{id}/instructions/sequence",
            params={"excludeHiddenItems": False},
        )
        return InstructionSequence(**response.json())

    def _get_instruction_set(self, *, id: InventoryId) -> InstructionSet:
        response = self.session.get(f"{self._instructions_base_path}/ids", params={"id": [id]})
        return InstructionSet(**response.json()["Items"][0])

    def _get_instruction(self, *, id: InventoryId, instruction_id: str) -> Instruction:
        response = self.session.get(
            f"{self._instructions_base_path}/{id}", params={"id": instruction_id}
        )
        return Instruction(**response.json())

    @validate_call
    def get_batch_instructions(self, *, id: InventoryId) -> BatchInstructions:
        """Get a formula's complete batching instructions in one read.

        Combines the formula's procedure table (ingredient, procedure stage, and
        reading rows with their values), the instruction texts authored on it
        with their per-row order, and the current version of the row order. Pass
        ``version`` when moving stages with
        [`move_procedure_stage`][albert.collections.instructions.InventoryInstructionsMixin.move_procedure_stage].
        Rows that have no values for the formula yet do not appear in ``rows``.

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            batch = client.inventory.get_batch_instructions(id="INV123")
            for row in batch.rows:
                print(row.type, row.name)
            for instruction in batch.instructions:
                print(instruction.id, instruction.name)
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula (format ``INV...``).

        Returns
        -------
        BatchInstructions
            The formula's procedure rows, instruction texts with their order,
            and the row-order version.
        """
        layout = self._get_instruction_layout(id=id)
        instruction_set = self._get_instruction_set(id=id)
        return BatchInstructions(
            id=layout.inventory_id or id,
            version=layout.version,
            rows=layout.rows,
            instructions=instruction_set.instructions,
            instruction_order=instruction_set.sequence,
        )

    @validate_call
    def add_instruction(
        self, *, id: InventoryId, text: str, design_row_id: str | None = None
    ) -> Instruction:
        """Add an instruction to a formula.

        To pin the instruction to a specific ingredient row, pass that row's
        unique ID as ``design_row_id`` (format ``DES...#ROW...``; match rows by
        name in
        [`get_batch_instructions`][albert.collections.instructions.InventoryInstructionsMixin.get_batch_instructions]
        results and read ``row_unique_id``). Without a row link, the instruction
        is formula-level. A new instruction is appended at the end of its order
        by default (its row's, or the formula-level one); reorder with
        [`set_instruction_order`][albert.collections.instructions.InventoryInstructionsMixin.set_instruction_order].

        !!! example
            ```python
            instruction = client.inventory.add_instruction(
                id="INV123", text="Take the pH of the batch"
            )
            instruction.id
            # 'ABI100'
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula to add the instruction to (format ``INV...``).
        text : str
            The instruction text (for example "Take the pH of the batch").
        design_row_id : str, optional
            The unique ID of the ingredient row to pin the instruction to
            (format ``DES...#ROW...``). When None, the instruction applies to
            the formula as a whole.

        Returns
        -------
        Instruction
            The added instruction, populated with its assigned ID.

        Raises
        ------
        ValueError
            If ``text`` is empty.
        """
        payload = self._build_create_payload(id=id, text=text, design_row_id=design_row_id)
        response = self.session.post(f"{self._instructions_base_path}/{id}", json=payload)
        return Instruction(**response.json())

    @validate_call
    def rename_instruction(
        self, *, id: InventoryId, instruction_id: str, text: str
    ) -> Instruction:
        """Rename an instruction on a formula.

        If ``text`` matches the current text, the instruction is returned
        unchanged.

        !!! example
            ```python
            updated = client.inventory.rename_instruction(
                id="INV123",
                instruction_id="ABI100",
                text="Take the pH of the batch twice",
            )
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula the instruction belongs to (format ``INV...``).
        instruction_id : str
            The ID of the instruction to rename (format ``ABI...``).
        text : str
            The new instruction text.

        Returns
        -------
        Instruction
            The renamed instruction.

        Notes
        -----
        Only the instruction text can be changed. Renames that change only
        letter casing are rejected.
        """
        existing = self._get_instruction(id=id, instruction_id=instruction_id)
        patch = self._build_rename_patch(
            instruction_id=instruction_id, old_text=existing.name or "", new_text=text
        )
        if patch is None:
            return existing
        self.session.patch(f"{self._instructions_base_path}/{id}", json=patch)
        return self._get_instruction(id=id, instruction_id=instruction_id)

    @validate_call
    def delete_instruction(self, *, id: InventoryId, instruction_id: str) -> None:
        """Delete an instruction from a formula.

        !!! example
            ```python
            client.inventory.delete_instruction(id="INV123", instruction_id="ABI100")
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula the instruction belongs to (format ``INV...``).
        instruction_id : str
            The ID of the instruction to delete (format ``ABI...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self._instructions_base_path}/{id}", json={"id": instruction_id})

    @validate_call
    def set_instruction_order(
        self,
        *,
        id: InventoryId,
        instruction_ids: list[str],
        design_row_id: str | None = None,
    ) -> InstructionSet:
        """Reorder the instructions within one row of a formula.

        Instructions are ordered independently inside each row they are pinned
        to, with one extra order for the formula-level (unpinned) instructions.
        Pass the row's full set of instruction IDs in the desired order; omit
        ``design_row_id`` to reorder the formula-level instructions. This does
        not change the order of the rows themselves (see
        [`move_procedure_stage`][albert.collections.instructions.InventoryInstructionsMixin.move_procedure_stage]).

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            batch = client.inventory.get_batch_instructions(id="INV123")
            ids = [i.id for i in batch.instructions]
            updated = client.inventory.set_instruction_order(
                id="INV123", instruction_ids=list(reversed(ids))
            )
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula whose instructions are reordered (format
            ``INV...``).
        instruction_ids : list[str]
            The IDs of the row's instructions in the desired order (format
            ``ABI...``). Must contain exactly the instructions currently in the
            row.
        design_row_id : str, optional
            The unique ID of the ingredient row whose instructions are reordered
            (format ``DES...#ROW...``). When None, the formula-level instructions
            are reordered.

        Returns
        -------
        InstructionSet
            The formula's instructions with their updated ordering.

        Raises
        ------
        ValueError
            If ``instruction_ids`` is not exactly the row's current set of
            instruction IDs, or the row has no instructions.
        """
        current = self._get_instruction_set(id=id)
        payload = self._build_instruction_order_payload(
            sequence=current.sequence,
            design_row_id=design_row_id,
            instruction_ids=instruction_ids,
        )
        self.session.patch(f"{self._instructions_base_path}/{id}/sequence", json=payload)
        return self._get_instruction_set(id=id)

    @validate_call
    def copy_instructions(
        self, *, id: InventoryId, target_ids: list[InventoryId]
    ) -> InstructionCopyResult:
        """Copy a formula's instructions and their order to other formulas.

        Every instruction of the source formula is recreated on each target
        formula with a fresh ID, keeping the same row pins and order. Formulas
        that already have instructions are skipped, not overwritten.

        !!! example
            ```python
            result = client.inventory.copy_instructions(
                id="INV123", target_ids=["INV456", "INV789"]
            )
            print(result.copied, result.skipped)
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula to copy instructions from (format ``INV...``).
        target_ids : list[InventoryId]
            The IDs of the formulas to copy instructions to (format ``INV...``).

        Returns
        -------
        InstructionCopyResult
            How many target formulas received the instructions and how many were
            skipped.
        """
        payload = {"sourceId": id, "targets": target_ids}
        response = self.session.post(f"{self._instructions_base_path}/copy", json=payload)
        return InstructionCopyResult(**response.json())

    @validate_call
    def move_procedure_stage(
        self,
        *,
        id: InventoryId,
        stage_row_id: str,
        reference_row_id: str,
        position: SequencePosition,
        version: int,
    ) -> InstructionSequence:
        """Move a procedure stage row to a new position in the row order.

        Only stage rows can be reordered; ingredient rows always follow the
        Sheet's Product Design. The stage identified by ``stage_row_id`` is
        placed directly above or below the row identified by
        ``reference_row_id``, which can be an ingredient row or another stage
        row.

        Both IDs use the unique row format ``DES...#ROW...``, which users rarely
        know directly. Find them by matching display names in the formula's
        batching instructions, as in the example below; each row's
        ``row_unique_id`` is the value to pass here.

        The ``version`` guards against conflicting edits: it must match the row
        order's current version, or the move is rejected and the batching
        instructions should be re-read before retrying. The updated row order
        (with its new version) is returned, so consecutive moves can chain off
        each result.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.instructions import SequencePosition

            client = Albert()
            batch = client.inventory.get_batch_instructions(id="INV123")
            ids_by_name = {row.name: row.row_unique_id for row in batch.rows}

            updated = client.inventory.move_procedure_stage(
                id="INV123",
                stage_row_id=ids_by_name["Heating"],
                reference_row_id=ids_by_name["Premix"],
                position=SequencePosition.BELOW,
                version=batch.version,
            )
            print(updated.version)
            ```

        Parameters
        ----------
        id : InventoryId
            The ID of the formula (format ``INV...``).
        stage_row_id : str
            The unique ID of the procedure stage row to move (format
            ``DES...#ROW...``).
        reference_row_id : str
            The unique ID of the row to place the moved stage next to (format
            ``DES...#ROW...``). Can be an ingredient row or another stage row.
        position : SequencePosition
            Whether to place the moved stage ``above`` or ``below`` the
            reference row.
        version : int
            The row order's current version, as returned by
            [`get_batch_instructions`][albert.collections.instructions.InventoryInstructionsMixin.get_batch_instructions].

        Returns
        -------
        InstructionSequence
            The updated row order, including its new ``version``.

        Notes
        -----
        Reordering is available only when it is enabled for the tenant; otherwise
        the call is rejected as not applicable.
        """
        payload = self._build_stage_move_payload(
            stage_row_id=stage_row_id,
            reference_row_id=reference_row_id,
            position=position,
            version=version,
        )
        self.session.patch(f"{self._inventory_base_path}/{id}/instructions/sequence", json=payload)
        return self._get_instruction_sequence(id=id)


class InstructionsCollection(InventoryInstructionsMixin):
    """Manage the batching instructions of formulas in the Albert platform.

    Nested under the inventory collection and accessed as
    ``client.inventory.instructions``. All methods come from
    [`InventoryInstructionsMixin`][albert.collections.instructions.InventoryInstructionsMixin],
    so ``client.inventory.instructions.add_instruction(...)`` and
    ``client.inventory.add_instruction(...)`` are equivalent.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        batch = client.inventory.instructions.get_batch_instructions(id="INV123")
        for instruction in batch.instructions:
            print(instruction.id, instruction.name)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for instruction requests.
    """

    def __init__(self, *, session: AlbertSession):
        """Initialize an InstructionsCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = self._instructions_base_path
