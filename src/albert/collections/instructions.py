from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import InventoryId
from albert.resources.instructions import (
    Instruction,
    InstructionCopyResult,
    InstructionLayout,
    InstructionOrder,
    InstructionSequence,
    InstructionSet,
    SequencePosition,
)

# The list endpoint pages at most this many instructions per fetch.
_INSTRUCTIONS_PAGE_SIZE = 100

# The bulk-read endpoint accepts at most this many formula IDs per call.
_INSTRUCTIONS_BULK_MAX_IDS = 15


class InstructionsCollection(BaseCollection):
    """Manage the batching instructions of formulas in the Albert platform.

    Batching instructions describe the procedure for making one specific formula
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]) as a batch:
    what you see on the formula's Instructions panel in the Albert interface.
    Two layers make it up:

    - **Instruction texts** ([`Instruction`][albert.resources.instructions.Instruction]):
      authored steps and notes, such as "Take the pH of the batch". Every
      instruction belongs to exactly one formula (its parent). An instruction
      can optionally be pinned to one of the formula's ingredient rows; without
      a pin it is a formula-level instruction. Instructions are created, edited,
      reordered within their row, copied between formulas, and deleted through
      this collection.
    - **The procedure table** ([`InstructionLayout`][albert.resources.instructions.InstructionLayout]
      and [`InstructionRow`][albert.resources.instructions.InstructionRow]):
      the formula's ingredient rows, parameter groups (procedure stages such as
      "Premix" or "Heating"), and parameter rows from its Worksheet, which give
      the instructions their structure. Row content is edited on the Worksheet;
      rows are read through
      [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id].

    The overall row order is held in an
    [`InstructionSequence`][albert.resources.instructions.InstructionSequence] and
    is determined in three places:

    - Ingredient rows always follow the order set on the Sheet's Product Design;
      they cannot be reordered per formula.
    - Parameter group rows default to the Sheet's Process Design order, but each
      formula can override the order of its own groups with
      [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence],
      placing a group above or below any other row (ingredient or parameter
      group). A parameter group stays with the ingredient it follows, so
      reordering ingredients on the Sheet carries the formula's groups along;
      groups newly added to the Sheet are appended at the end.
    - Parameter rows (the readings and targets inside a group, such as
      temperature or mixing time) belong to their parent parameter group and
      move with it; they are not individually reorderable.

    Reordering rows with
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence]
    uses unique row IDs (format ``DES...#ROW...``), which are not the names or
    IDs users usually have in hand. To find them, fetch the formula's
    instruction rows with
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id]
    and match rows by their display ``name`` or by the entity behind the row
    (``id`` holds the parameter group ID or the ingredient's inventory ID); each
    row's ``row_unique_id`` is the value to pass when reordering. Rows that have
    no values for the formula yet do not appear in the rows, but are
    listed by
    [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].

    This collection is accessed as ``client.inventory.instructions``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        instructions = client.inventory.instructions
        for instruction in instructions.get_all(parent_id="INV123"):
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

    Methods
    -------
    get_all(parent_id, created_by, updated_by, max_items) -> Iterator[Instruction]
        Get instructions, filtered to one formula or one author.
    get_by_id(parent_id, id) -> Instruction
        Get a single instruction by its ID.
    get_by_parent_ids(parent_ids) -> list[InstructionSet]
        Get the instructions of several formulas in one call.
    create(instruction) -> Instruction
        Add an instruction to a formula.
    update(instruction) -> Instruction
        Update an existing instruction's text.
    delete(parent_id, id) -> None
        Delete an instruction from a formula.
    update_row_sequence(parent_id, instruction_ids, design_row_id) -> InstructionSet
        Reorder the instructions within one row of a formula.
    copy(source_id, target_ids) -> InstructionCopyResult
        Copy a formula's instructions and their order to other formulas.
    get_by_inventory_id(inventory_id) -> InstructionLayout
        Get the procedure table of a formula: its rows with their values.
    get_sequence(inventory_id, exclude_hidden=False) -> InstructionSequence
        Get the ordered instruction row sequence of a formula.
    update_sequence(inventory_id, source_id, reference_id, position, version) -> InstructionSequence
        Move a parameter group row to a new position in the instruction sequence.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize an InstructionsCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{InstructionsCollection._api_version}/instructions"
        self._inventory_base_path = f"/api/{InstructionsCollection._api_version}/inventories"

    @staticmethod
    def _resolve_list_params(
        *,
        parent_id: str | None,
        created_by: str | None,
        updated_by: str | None,
    ) -> dict[str, str]:
        chosen = {"parentId": parent_id, "createdBy": created_by, "updatedBy": updated_by}
        provided = {k: v for k, v in chosen.items() if v is not None}
        if len(provided) != 1:
            raise ValueError(
                "Exactly one of parent_id, created_by, or updated_by must be provided."
            )
        return provided

    @staticmethod
    def _build_row_sequence_payload(
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
    def _build_sequence_move_payload(
        *, source_id: str, reference_id: str, position: SequencePosition, version: int
    ) -> dict:
        return {
            "data": [
                {
                    "operation": "update",
                    "attribute": "sequence",
                    "sourceId": source_id,
                    "referenceId": reference_id,
                    "position": position.value,
                    "version": version,
                }
            ]
        }

    @validate_call
    def get_all(
        self,
        *,
        parent_id: InventoryId | None = None,
        created_by: str | None = None,
        updated_by: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Instruction]:
        """Get instructions, filtered to one formula or one author.

        Exactly one filter must be provided: a formula (``parent_id``), a creator
        (``created_by``), or a last editor (``updated_by``). Results are returned
        as a lazily paginated iterator; when filtering by formula, instructions
        come back in display order.

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            for instruction in client.inventory.instructions.get_all(parent_id="INV123"):
                print(instruction.id, instruction.name)
            ```

        Parameters
        ----------
        parent_id : InventoryId, optional
            Only instructions belonging to this formula (format ``INV...``).
        created_by : str, optional
            Only instructions created by this user ID.
        updated_by : str, optional
            Only instructions last edited by this user ID.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[Instruction]
            A lazily paginated iterator of matching instructions.

        Raises
        ------
        ValueError
            If zero or more than one of the filters is provided.
        """
        params = self._resolve_list_params(
            parent_id=parent_id, created_by=created_by, updated_by=updated_by
        )
        params["limit"] = _INSTRUCTIONS_PAGE_SIZE
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Instruction.model_validate(x) for x in items],
        )

    @validate_call
    def get_by_id(self, *, parent_id: InventoryId, id: str) -> Instruction:
        """Get a single instruction by its ID.

        !!! example
            ```python
            instruction = client.inventory.instructions.get_by_id(
                parent_id="INV123", id="ABI100"
            )
            instruction.name
            # 'Take the pH of the batch'
            ```

        Parameters
        ----------
        parent_id : InventoryId
            The ID of the formula the instruction belongs to (format ``INV...``).
        id : str
            The ID of the instruction to retrieve (format ``ABI...``).

        Returns
        -------
        Instruction
            The fully populated instruction.
        """
        response = self.session.get(f"{self.base_path}/{parent_id}", params={"id": id})
        return Instruction(**response.json())

    @validate_call
    def get_by_parent_ids(self, *, parent_ids: list[InventoryId]) -> list[InstructionSet]:
        """Get the instructions of several formulas in one call.

        Each formula comes back with its instructions in display order and the
        per-row ordering of those instructions. Formulas without instructions
        yet are returned empty. At most 15 formulas can be fetched per call.

        !!! example
            ```python
            sets = client.inventory.instructions.get_by_parent_ids(
                parent_ids=["INV123", "INV456"]
            )
            for s in sets:
                print(s.id, len(s.instructions))
            ```

        Parameters
        ----------
        parent_ids : list[InventoryId]
            The IDs of the formulas to fetch instructions for (format ``INV...``).
            Maximum 15 per call.

        Returns
        -------
        list[InstructionSet]
            One entry per requested formula, with its instructions and ordering.

        Raises
        ------
        ValueError
            If more than 15 formula IDs are provided.
        """
        if not parent_ids or len(parent_ids) > _INSTRUCTIONS_BULK_MAX_IDS:
            raise ValueError("Provide between 1 and 15 formula IDs.")
        response = self.session.get(f"{self.base_path}/ids", params={"id": parent_ids})
        return [InstructionSet(**x) for x in response.json()["Items"]]

    @validate_call
    def create(self, *, instruction: Instruction) -> Instruction:
        """Add an instruction to a formula.

        The instruction's ``parent_id`` selects the formula and is required.
        To pin the instruction to a specific ingredient row, set
        ``design.design_row_id`` to that row's unique ID (format
        ``DES...#ROW...``; match rows by name in
        [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id]
        results and read ``row_unique_id``). Without a row link, the instruction
        is formula-level. A new instruction is placed after the existing
        instructions in its row; reorder with
        [`update_row_sequence`][albert.collections.instructions.InstructionsCollection.update_row_sequence].

        !!! example
            ```python
            from albert import Albert
            from albert.resources.instructions import Instruction

            client = Albert()
            instruction = client.inventory.instructions.create(
                instruction=Instruction(
                    name="Take the pH of the batch", parent_id="INV123"
                )
            )
            print(instruction.id)
            ```

        Parameters
        ----------
        instruction : Instruction
            The instruction to create. Requires ``name`` and ``parent_id``.

        Returns
        -------
        Instruction
            The created instruction, populated with its assigned ID.

        Raises
        ------
        ValueError
            If the instruction has no ``name`` or ``parent_id``.
        """
        if not instruction.name or not instruction.parent_id:
            raise ValueError("Instruction requires a name and a parent_id.")
        design_payload: dict[str, str] = {"productId": instruction.parent_id}
        if instruction.design and instruction.design.design_row_id:
            design_payload["designRowId"] = instruction.design.design_row_id
        response = self.session.post(
            f"{self.base_path}/{instruction.parent_id}",
            json={
                "name": instruction.name,
                "parentId": instruction.parent_id,
                "Design": design_payload,
            },
        )
        return Instruction(**response.json())

    @validate_call
    def update(self, *, instruction: Instruction) -> Instruction:
        """Update an instruction's text.

        Fetch an instruction (e.g. via [`get_by_id`][albert.collections.instructions.InstructionsCollection.get_by_id]),
        modify its ``name``, then pass it here. The instruction is matched by its
        ``id`` and ``parent_id``. If nothing changed, the existing instruction is
        returned unmodified.

        !!! example
            ```python
            instruction = client.inventory.instructions.get_by_id(
                parent_id="INV123", id="ABI100"
            )
            instruction.name = "Take the pH of the batch twice"
            updated = client.inventory.instructions.update(instruction=instruction)
            ```

        Parameters
        ----------
        instruction : Instruction
            The instruction with updated fields. Must include ``id`` and
            ``parent_id``.

        Returns
        -------
        Instruction
            The updated instruction.

        Notes
        -----
        The following fields can be updated: ``name``.
        """
        existing = self.get_by_id(parent_id=instruction.parent_id, id=instruction.id)
        if existing.name == instruction.name:
            return existing
        payload = {
            "id": instruction.id,
            "data": [
                {
                    "operation": "update",
                    "attribute": "name",
                    "oldValue": existing.name or "",
                    "newValue": instruction.name or "",
                }
            ],
        }
        self.session.patch(f"{self.base_path}/{instruction.parent_id}", json=payload)
        return self.get_by_id(parent_id=instruction.parent_id, id=instruction.id)

    @validate_call
    def delete(self, *, parent_id: InventoryId, id: str) -> None:
        """Delete an instruction from a formula.

        !!! example
            ```python
            client.inventory.instructions.delete(parent_id="INV123", id="ABI100")
            ```

        Parameters
        ----------
        parent_id : InventoryId
            The ID of the formula the instruction belongs to (format ``INV...``).
        id : str
            The ID of the instruction to delete (format ``ABI...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{parent_id}", json={"id": id})

    @validate_call
    def update_row_sequence(
        self,
        *,
        parent_id: InventoryId,
        instruction_ids: list[str],
        design_row_id: str | None = None,
    ) -> InstructionSet:
        """Reorder the instructions within one row of a formula.

        Instructions are ordered independently inside each row they are pinned
        to, with one extra order for the formula-level (unpinned) instructions.
        Pass the row's full set of instruction IDs in the desired order; omit
        ``design_row_id`` to reorder the formula-level instructions. This does
        not change the order of the rows themselves (see
        [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence]).

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            instructions = client.inventory.instructions
            current = instructions.get_by_parent_ids(parent_ids=["INV123"])[0]
            ids = [i.id for i in current.instructions]
            updated = instructions.update_row_sequence(
                parent_id="INV123", instruction_ids=list(reversed(ids))
            )
            ```

        Parameters
        ----------
        parent_id : InventoryId
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
        current = self.get_by_parent_ids(parent_ids=[parent_id])[0]
        payload = self._build_row_sequence_payload(
            sequence=current.sequence,
            design_row_id=design_row_id,
            instruction_ids=instruction_ids,
        )
        self.session.patch(f"{self.base_path}/{parent_id}/sequence", json=payload)
        return self.get_by_parent_ids(parent_ids=[parent_id])[0]

    @validate_call
    def copy(
        self, *, source_id: InventoryId, target_ids: list[InventoryId]
    ) -> InstructionCopyResult:
        """Copy a formula's instructions and their order to other formulas.

        Every instruction of the source formula is recreated on each target
        formula with a fresh ID, keeping the same row pins and order. Formulas
        that already have instructions are skipped, not overwritten.

        !!! example
            ```python
            result = client.inventory.instructions.copy(
                source_id="INV123", target_ids=["INV456", "INV789"]
            )
            print(result.copied, result.skipped)
            ```

        Parameters
        ----------
        source_id : InventoryId
            The ID of the formula to copy instructions from (format ``INV...``).
        target_ids : list[InventoryId]
            The IDs of the formulas to copy instructions to (format ``INV...``).

        Returns
        -------
        InstructionCopyResult
            How many target formulas received the instructions and how many were
            skipped.
        """
        payload = {"sourceId": source_id, "targets": target_ids}
        response = self.session.post(f"{self.base_path}/copy", json=payload)
        return InstructionCopyResult(**response.json())

    @validate_call
    def get_by_inventory_id(self, *, inventory_id: InventoryId) -> InstructionLayout:
        """Get the procedure table of a formula: its rows with their values.

        Returns every row of the formula's procedure in display order:
        ingredient rows, parameter groups (procedure stages), and parameter
        rows, each with its values for the relevant Worksheet columns. To get
        only the row order without the values, use
        [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].
        See [`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
        for how the overall order is determined.

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            layout = client.inventory.instructions.get_by_inventory_id(inventory_id="INV123")
            for row in layout.rows:
                print(row.type, row.name)
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the formula inventory item (format ``INV...``).

        Returns
        -------
        InstructionLayout
            The formula's rows, including the sequence ``version``.
        """
        path = f"{self._inventory_base_path}/{inventory_id}/instructions"
        response = self.session.get(path)
        return InstructionLayout(**response.json())

    @validate_call
    def get_sequence(
        self, *, inventory_id: InventoryId, exclude_hidden: bool = False
    ) -> InstructionSequence:
        """Get the ordered instruction row sequence of a formula.

        The sequence lists each row of the formula's procedure in display order.
        If the order has never been customized, it matches the Sheet the formula
        lives on; see
        [`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
        for how the order is determined. The returned ``version`` is required
        when reordering rows with
        [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            sequence = client.inventory.instructions.get_sequence(inventory_id="INV123")
            for row in sequence.rows:
                print(item.row_id, item.is_hidden)
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the formula inventory item (format ``INV...``).
        exclude_hidden : bool, optional
            When True, omit rows that are currently hidden on the Worksheet.
            Default is False.

        Returns
        -------
        InstructionSequence
            The formula's instruction row sequence, including its ``version``.
        """
        path = f"{self._inventory_base_path}/{inventory_id}/instructions/sequence"
        response = self.session.get(path, params={"excludeHiddenItems": exclude_hidden})
        return InstructionSequence(**response.json())

    @validate_call
    def update_sequence(
        self,
        *,
        inventory_id: InventoryId,
        source_id: str,
        reference_id: str,
        position: SequencePosition,
        version: int,
    ) -> InstructionSequence:
        """Move a parameter group row to a new position in the formula's procedure.

        Only parameter group rows (the stages of the procedure) can be
        reordered; ingredient rows always follow the Sheet's Product Design. The
        row identified by ``source_id`` is placed directly above or below the row
        identified by ``reference_id``, which can be an ingredient row or another
        parameter group row.

        Both IDs use the unique row format ``DES...#ROW...``, which users rarely
        know directly. Find them by matching display names in the formula's
        instruction rows, as in the example below; each row's ``row_unique_id``
        is the value to pass here.

        The ``version`` guards against conflicting edits: it must match the
        sequence's current version, or the move is rejected and the sequence
        should be re-fetched before retrying. The updated sequence (with its new
        version) is returned, so consecutive moves can chain off each result.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.instructions import SequencePosition

            client = Albert()
            instructions = client.inventory.instructions
            layout = instructions.get_by_inventory_id(inventory_id="INV123")
            ids_by_name = {row.name: row.row_unique_id for row in layout.rows}

            sequence = instructions.get_sequence(inventory_id="INV123")
            updated = instructions.update_sequence(
                inventory_id="INV123",
                source_id=ids_by_name["Heating"],
                reference_id=ids_by_name["Premix"],
                position=SequencePosition.BELOW,
                version=sequence.version,
            )
            print(updated.version)
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the formula inventory item (format ``INV...``).
        source_id : str
            The unique ID of the parameter group row to move (format ``DES...#ROW...``).
        reference_id : str
            The unique ID of the row to place the moved row next to (format
            ``DES...#ROW...``). Can be an ingredient row or another parameter
            group row.
        position : SequencePosition
            Whether to place the moved row ``above`` or ``below`` the reference row.
        version : int
            The sequence's current version, as returned by
            [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].

        Returns
        -------
        InstructionSequence
            The updated instruction row sequence, including its new ``version``.

        Notes
        -----
        Reordering is available only when it is enabled for the tenant; otherwise
        the call is rejected as not applicable.
        """
        path = f"{self._inventory_base_path}/{inventory_id}/instructions/sequence"
        payload = self._build_sequence_move_payload(
            source_id=source_id, reference_id=reference_id, position=position, version=version
        )
        self.session.patch(path, json=payload)
        return self.get_sequence(inventory_id=inventory_id)
