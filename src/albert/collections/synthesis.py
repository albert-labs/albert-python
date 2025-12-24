from __future__ import annotations

from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.exceptions import AlbertException
from albert.resources.synthesis import ReactantValues, RowSequence, Synthesis


class SynthesisCollection(BaseCollection):
    """
    Collection for interacting with synthesis records used by notebook Ketcher blocks.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "status", "hide_reaction_worksheet"}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the SynthesisCollection.

        Parameters
        ----------
        session : AlbertSession
            The Albert session information.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SynthesisCollection._api_version}/synthesis"

    @validate_call
    def create(
        self, *, parent_id: NotebookId | str, name: str, block_id: str, smiles: str | None = None
    ) -> Synthesis:
        """
        Create a synthesis record for a notebook Ketcher block.

        Parameters
        ----------
        parent_id : NotebookId | str
            The notebook ID that owns the synthesis record.
        name : str
            The synthesis name.
        block_id : str
            The Ketcher block ID associated with the synthesis.
        smiles : str | None, optional
            The initial SMILES string for the synthesis.

        Returns
        -------
        Synthesis
            The created synthesis record.
        """
        payload = {"name": name, "blockId": block_id, "smiles": smiles}
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
        """
        Retrieve a synthesis record by ID.

        Parameters
        ----------
        id : SynthesisId
            The synthesis ID.
        include_recommendations : bool, optional
            Whether to include recommendations in the response.
        include_predictions : bool, optional
            Whether to include predictions in the response.
        version : str | None, optional
            The specific version to retrieve.

        Returns
        -------
        Synthesis
            The requested synthesis record.
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
        """
        Update the Ketcher canvas data for a synthesis record.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The synthesis ID.
        smiles : str
            The updated SMILES string.
        data : str
            The serialized canvas data.
        png : str
            The base64-encoded PNG for the canvas.

        Returns
        -------
        Synthesis
            The updated synthesis record.
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
        """
        Update a synthesis record.

        Parameters
        ----------
        synthesis : Synthesis
            The synthesis record containing updated fields.

        Returns
        -------
        Synthesis
            The refreshed synthesis record.

        Raises
        ------
        AlbertException
            If the synthesis record is missing an ID.
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
        """
        Update the values for a reactant row.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The synthesis ID.
        row_id : str
            The reactant row ID to update.
        values : ReactantValues
            The values to apply to the reactant row.

        Returns
        -------
        Synthesis
            The updated synthesis record.
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
        """
        Initialize the reactant/product table for a synthesis.

        Parameters
        ----------
        synthesis_id : SynthesisId
            The synthesis ID.

        Returns
        -------
        Synthesis
            The synthesis record.
        """
        synthesis = self.get_by_id(id=synthesis_id)
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
            The patch payload to send.

        Returns
        -------
        None
        """
        self.session.patch(
            url=f"{self.base_path}/{synthesis_id}",
            json=payload,
        )
