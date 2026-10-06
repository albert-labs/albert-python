from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import InventoryId
from albert.resources.instructions import (
    InstructionSequence,
    InventoryInstructions,
    SequencePosition,
)


class InstructionsCollection(BaseCollection):
    """Manage the formula-specific batching instructions of formulas in the Albert platform.

    Batching instructions describe the procedure for making one specific formula
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]) as a batch: the
    ordered steps and measurements that turn its ingredients into the final
    product. They are a formula-specific view of the formula's
    [`Sheet`][albert.resources.sheets.Sheet], combining its ingredient rows from
    the Product Design with the parameter groups (procedure stages such as
    "Premix" or "Heating") and their measurement rows from the Process Design.
    Each row carries its values for the relevant Worksheet columns, so a formula
    made in several batch columns shows one value per column.

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
    - Measurement rows belong to their parent parameter group and move with it;
      they are not individually reorderable.

    This collection is accessed as ``client.instructions``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        instructions = client.instructions.get_by_inventory_id(inventory_id="INV123")
        for item in instructions.items:
            print(item.type, item.name)
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
    get_by_inventory_id(inventory_id) -> InventoryInstructions
        Get the batching instructions of a formula.
    get_sequence(inventory_id, exclude_hidden=False) -> InstructionSequence
        Get the ordered instruction sequence of a formula.
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
        self.base_path = f"/api/{InstructionsCollection._api_version}/inventories"

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
    def get_by_inventory_id(self, *, inventory_id: InventoryId) -> InventoryInstructions:
        """Get the batching instructions of a formula.

        Returns every instruction row of the formula's procedure in display
        order: ingredient rows, parameter groups (procedure stages), and
        measurement rows, each with its values for the relevant Worksheet
        columns. To get only the row order without the values, use
        [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].
        See [`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
        for how the overall order is determined.

        !!! example
            ```python
            from albert import Albert
            client = Albert()
            instructions = client.instructions.get_by_inventory_id(inventory_id="INV123")
            for item in instructions.items:
                print(item.type, item.name)
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the formula inventory item (format ``INV...``).

        Returns
        -------
        InventoryInstructions
            The formula's batch instructions, including the sequence ``version``.
        """
        path = f"{self.base_path}/{inventory_id}/instructions"
        response = self.session.get(path)
        return InventoryInstructions(**response.json())

    @validate_call
    def get_sequence(
        self, *, inventory_id: InventoryId, exclude_hidden: bool = False
    ) -> InstructionSequence:
        """Get the ordered instruction sequence of a formula.

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
            sequence = client.instructions.get_sequence(inventory_id="INV123")
            for item in sequence.sequence:
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
            The formula's instruction sequence, including its ``version``.
        """
        path = f"{self.base_path}/{inventory_id}/instructions/sequence"
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
        parameter group row. Both IDs use the unique row format
        ``DES...#ROW...``, as found on
        [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence]
        results.

        The ``version`` guards against conflicting edits: it must match the
        sequence's current version, or the move is rejected and the sequence
        should be re-fetched before retrying. The updated sequence (with its new
        version) is returned, so consecutive moves can chain off each result.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.instructions import SequencePosition

            client = Albert()
            sequence = client.instructions.get_sequence(inventory_id="INV123")
            updated = client.instructions.update_sequence(
                inventory_id="INV123",
                source_id="DES413129#ROW42",
                reference_id="DES413126#ROW15",
                position=SequencePosition.ABOVE,
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
            The updated instruction sequence, including its new ``version``.

        Notes
        -----
        Reordering is available only when it is enabled for the tenant; otherwise
        the call is rejected as not applicable.
        """
        path = f"{self.base_path}/{inventory_id}/instructions/sequence"
        payload = self._build_sequence_move_payload(
            source_id=source_id, reference_id=reference_id, position=position, version=version
        )
        self.session.patch(path, json=payload)
        return self.get_sequence(inventory_id=inventory_id)
