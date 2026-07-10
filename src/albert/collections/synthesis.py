from __future__ import annotations

import uuid
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.exceptions import AlbertException
from albert.resources.synthesis import ReactantValues, RowSequence, Synthesis


class SynthesisCollection(BaseCollection):
    """Manage synthesis (reaction) records on the Albert platform.

    A synthesis record documents a chemical reaction on a drawing canvas: the
    reactants and products of the reaction, drawn as chemical structures (via the
    Ketcher structure editor) and laid out in a reaction worksheet table. Each row
    of that table is a reaction participant (a reactant or a product), and its
    quantities (mass, moles, equivalents, concentration) can be filled in.

    A synthesis always belongs to a block inside a Notebook (see
    :class:`~albert.collections.notebooks.NotebookCollection`); the parent notebook
    is supplied when the record is created. Synthesis records are referenced by
    their Synthesis ID (format ``SYN...``, e.g. ``"SYNA1"``).

    A typical flow is: :meth:`create` the record, draw the reaction and push the
    canvas with :meth:`update_canvas_data`, initialize the reactant/product table
    with :meth:`create_reactant_productant_table`, then set per-row quantities with
    :meth:`update_reactant_row_values`.

    This collection is accessed as ``client.synthesis``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for synthesis requests.

    Methods
    -------
    create(parent_id, name, block_id=None, smiles=None) -> Synthesis
        Create a synthesis record for a notebook Ketcher block.
    get_by_id(id, include_recommendations=False, include_predictions=False, version=None) -> Synthesis
        Retrieve a single synthesis record by its Synthesis ID.
    update(synthesis) -> Synthesis
        Apply changes to an existing synthesis record.
    update_canvas_data(synthesis_id, smiles, data, png) -> Synthesis
        Replace the drawn reaction (SMILES, canvas data, and preview image).
    update_reactant_row_values(synthesis_id, row_id, values) -> Synthesis
        Set the quantities (mass, moles, eq, concentration) for one reactant row.
    create_reactant_productant_table(synthesis_id) -> Synthesis
        Initialize the reactant/product table and reveal the reaction worksheet.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        synthesis = client.synthesis.create(
            parent_id="NTBA1",
            name="Amide coupling",
        )
        print(synthesis.id)
        ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "status", "hide_reaction_worksheet"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a SynthesisCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SynthesisCollection._api_version}/synthesis"

    @validate_call
    def create(
        self,
        *,
        parent_id: NotebookId | str,
        name: str,
        block_id: str | None = None,
        smiles: str | None = None,
    ) -> Synthesis:
        """Create a synthesis record for a notebook Ketcher block.

        Use this to start documenting a reaction inside a notebook. The new record
        is empty; draw the reaction and push it with :meth:`update_canvas_data`, and
        build out the reactant/product table with
        :meth:`create_reactant_productant_table`.

        Parameters
        ----------
        parent_id : NotebookId or str
            The Notebook ID that owns the synthesis record (format ``NTB...``).
        name : str
            A human-readable name for the synthesis.
        block_id : str, optional
            The Ketcher block ID to associate with the synthesis. A new ID is
            generated when not provided.
        smiles : str, optional
            An initial reaction SMILES string to seed the canvas.

        Returns
        -------
        Synthesis
            The created synthesis record, populated with its assigned Synthesis ID.

        Examples
        --------
        !!! example
            ```python
            synthesis = client.synthesis.create(
                parent_id="NTBA1",
                name="Amide coupling",
                smiles="CC(=O)O.CN>>CC(=O)NC",
            )
            synthesis.id
            # 'SYNA1'
            ```
        """
        payload: dict[str, Any] = {"name": name, "blockId": block_id or str(uuid.uuid4())}
        if smiles is not None:
            payload["smiles"] = smiles
        response = self.session.post(
            url=self.base_path,
            params={"parentId": parent_id},
            json=payload,
        )
        return Synthesis(**response.json())

    @validate_call
    def get_by_id(
        self,
        *,
        id: SynthesisId,
        include_recommendations: bool = False,
        include_predictions: bool = False,
        version: str | None = None,
    ) -> Synthesis:
        """Retrieve a synthesis record by its Synthesis ID.

        Parameters
        ----------
        id : SynthesisId
            The Synthesis ID to retrieve (format ``SYN...``, e.g. ``"SYNA1"``).
        include_recommendations : bool, optional
            When True, include reaction recommendations in the response.
            Defaults to False.
        include_predictions : bool, optional
            When True, include reaction predictions in the response.
            Defaults to False.
        version : str, optional
            A specific version of the record to retrieve. Defaults to the latest.

        Returns
        -------
        Synthesis
            The requested synthesis record.

        Examples
        --------
        !!! example
            ```python
            synthesis = client.synthesis.get_by_id(id="SYNA1")
            print(synthesis.name)
            ```
        """
        params: dict[str, Any] = {
            "recommendations": include_recommendations,
            "predictions": include_predictions,
        }
        if version:
            params["version"] = version
        response = self.session.get(
            url=f"{self.base_path}/{id}",
            params=params,
        )
        return Synthesis(**response.json())

    @validate_call
    def update_canvas_data(
        self, *, synthesis_id: SynthesisId, smiles: str, data: str, png: str
    ) -> Synthesis:
        """Update the Ketcher canvas data for a synthesis record.

        Use this to save the drawn reaction after editing it in the structure
        editor. It replaces the reaction SMILES, the serialized canvas, and the
        rendered preview image together.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The Synthesis ID to update (format ``SYN...``).
        smiles : str
            The updated reaction SMILES string.
        data : str
            The serialized canvas data from the structure editor.
        png : str
            The base64-encoded PNG preview of the canvas.

        Returns
        -------
        Synthesis
            The updated synthesis record.

        Examples
        --------
        !!! example
            ```python
            synthesis = client.synthesis.update_canvas_data(
                synthesis_id="SYNA1",
                smiles="CC(=O)O.CN>>CC(=O)NC",
                data=serialized_canvas,
                png=base64_png,
            )
            ```
        """
        payload = {
            "smiles": smiles,
            "canvasData": {"data": data, "png": png},
        }
        response = self.session.put(
            url=f"{self.base_path}/{synthesis_id}",
            json=payload,
        )
        return Synthesis(**response.json())

    @validate_call
    def update(self, *, synthesis: Synthesis) -> Synthesis:
        """Apply changes to an existing synthesis record.

        Fetch the record with :meth:`get_by_id`, modify the updatable fields on the
        returned object, then pass it here. Only the fields listed in Notes are
        sent; other differences are ignored. If nothing changed, the existing
        record is returned unmodified.

        Parameters
        ----------
        synthesis : Synthesis
            The synthesis record containing updated fields. Its ``id`` must be set.

        Returns
        -------
        Synthesis
            The refreshed synthesis record.

        Raises
        ------
        AlbertException
            If the synthesis record is missing an ID.

        Notes
        -----
        The following fields can be updated: ``name``, ``status``,
        ``hide_reaction_worksheet``.

        Examples
        --------
        !!! example
            ```python
            synthesis = client.synthesis.get_by_id(id="SYNA1")
            synthesis.name = "Amide coupling (revised)"
            updated = client.synthesis.update(synthesis=synthesis)
            ```
        """
        if synthesis.id is None:
            msg = "Synthesis id is required to update the record."
            raise AlbertException(msg)
        existing = self.get_by_id(id=synthesis.id)
        patch_data = self._generate_patch_payload(existing=existing, updated=synthesis)
        if len(patch_data.data) == 0:
            return existing
        self.session.patch(
            url=f"{self.base_path}/{synthesis.id}",
            json=patch_data.model_dump(by_alias=True, mode="json"),
        )
        return self.get_by_id(id=synthesis.id)

    @validate_call
    def update_reactant_row_values(
        self,
        *,
        synthesis_id: SynthesisId,
        row_id: str,
        values: ReactantValues,
    ) -> Synthesis:
        """Update the quantities for a single reactant row.

        Sets the mass, moles, equivalents, and concentration for one row of the
        reaction worksheet table. The row is identified by its row ID, which can be
        read from ``Synthesis.reactants`` (each
        :class:`~albert.resources.synthesis.ReactionParticipant` has a ``row_id``)
        or from ``Synthesis.row_sequence.reactants``.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The Synthesis ID to update (format ``SYN...``).
        row_id : str
            The reactant row ID to update.
        values : ReactantValues
            The quantities to apply to the reactant row.

        Returns
        -------
        Synthesis
            The updated synthesis record.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.synthesis import ReactantValues
            synthesis = client.synthesis.get_by_id(id="SYNA1")
            row_id = synthesis.reactants[0].row_id
            updated = client.synthesis.update_reactant_row_values(
                synthesis_id="SYNA1",
                row_id=row_id,
                values=ReactantValues(mass=10.0, eq=1.0),
            )
            ```
        """
        payload = {
            "data": [
                {
                    "rowId": row_id,
                    "operation": "update",
                    "attribute": "values",
                    "newValue": values.model_dump(by_alias=True, mode="json"),
                }
            ]
        }
        self.session.patch(
            url=f"{self.base_path}/{synthesis_id}/reactants/rows",
            json=payload,
        )
        return self.get_by_id(id=synthesis_id)

    @validate_call
    def create_reactant_productant_table(self, *, synthesis_id: SynthesisId) -> Synthesis:
        """Initialize the reactant/product table for a synthesis.

        Sets up the reaction worksheet so quantities can be entered: it seeds the
        first reactant row (concentration 100), reveals the reaction worksheet, and
        attaches the backing inventory. If the table has already been initialized
        (the record already has an inventory ID) or there are no reactant rows to
        seed, the record is returned unchanged.

        Call this after the reaction has been drawn (see
        :meth:`update_canvas_data`) and before setting per-row quantities with
        :meth:`update_reactant_row_values`.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The Synthesis ID to initialize (format ``SYN...``).

        Returns
        -------
        Synthesis
            The synthesis record with its reactant/product table initialized.

        Examples
        --------
        !!! example
            ```python
            synthesis = client.synthesis.create_reactant_productant_table(
                synthesis_id="SYNA1",
            )
            ```
        """
        synthesis = self.get_by_id(id=synthesis_id)
        if synthesis.inventory_id is not None:
            return synthesis
        row_sequence: RowSequence | None = synthesis.row_sequence
        reactant_row_ids = row_sequence.reactants if row_sequence else []
        if not reactant_row_ids and synthesis.reactants:
            reactant_row_ids = [r.row_id for r in synthesis.reactants if r.row_id]
        if not reactant_row_ids:
            return synthesis

        self.update_reactant_row_values(
            synthesis_id=synthesis_id,
            row_id=reactant_row_ids[0],
            values=ReactantValues(
                mass=None,
                moles=None,
                eq=None,
                concentration=100,
            ),
        )

        self._send_patch(
            synthesis_id=synthesis_id,
            payload={
                "data": [
                    {
                        "attribute": "hideReactionWorksheet",
                        "operation": "update",
                        "newValue": "false",
                    }
                ]
            },
        )

        self._send_patch(
            synthesis_id=synthesis_id,
            payload={
                "data": [
                    {
                        "attribute": "inventoryId",
                        "operation": "add",
                    }
                ]
            },
        )
        return self.get_by_id(id=synthesis_id)

    def _send_patch(self, *, synthesis_id: SynthesisId, payload: dict[str, Any]) -> None:
        """
        Send a PATCH request to the synthesis endpoint.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The synthesis ID.
        payload : dict[str, Any]
            Patch request data to send.

        Returns
        -------
        None
        """
        self.session.patch(
            url=f"{self.base_path}/{synthesis_id}",
            json=payload,
        )
