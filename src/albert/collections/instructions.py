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
    """Manage batch instructions for formula inventory items in the Albert platform.

    Batch instructions are the ordered rows that describe how a formula is made:
    its ingredient rows from the Product Design, its process groups (the stages
    of the procedure) from the Process Design, and the measurement rows inside
    them. Each row carries its values for the relevant Worksheet columns, so a
    formula made in several batch columns shows one value per column.

    Every formula inventory item
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]) has one set of
    instructions, identified by the formula's inventory ID. The order of the rows
    is held in an [`InstructionSequence`][albert.resources.instructions.InstructionSequence]:
    ingredient rows always follow the Worksheet, while process group rows can be
    reordered to customize the procedure's stage order for that formula.

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
        Get the batch instructions of a formula inventory item.
    get_sequence(inventory_id, exclude_hidden=False) -> InstructionSequence
        Get the ordered instruction sequence of a formula inventory item.
    update_sequence(inventory_id, source_id, reference_id, position, version) -> InstructionSequence
        Move a process group row to a new position in the instruction sequence.
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
        """Get the batch instructions of a formula inventory item.

        Returns every instruction row of the formula in display order: ingredient
        rows, process groups, and measurement rows, each with its values for the
        relevant Worksheet columns. To get only the row order without the values,
        use [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].

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
        """Get the ordered instruction sequence of a formula inventory item.

        The sequence lists each instruction row in display order. If the order
        has never been customized, it matches the Worksheet. The returned
        ``version`` is required when reordering rows with
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
        """Move a process group row to a new position in the instruction sequence.

        Only process group rows (the stages of the procedure) can be reordered;
        ingredient rows always follow the Worksheet. The row identified by
        ``source_id`` is placed directly above or below the row identified by
        ``reference_id``. Both IDs use the unique row format ``DES...#ROW...``,
        as found on [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence]
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
            The unique ID of the process group row to move (format ``DES...#ROW...``).
        reference_id : str
            The unique ID of the row to place the moved row next to (format
            ``DES...#ROW...``).
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
