from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.core.utils import ensure_list
from albert.exceptions import AlbertException
from albert.resources.synthesis import (
    ReactantValues,
    RowSequence,
    Synthesis,
    SynthesisSearchItem,
)


class SynthesisCollection(BaseCollection):
    """Manage synthesis (reaction) records on the Albert platform.

    A synthesis record documents a chemical reaction on a drawing canvas: the
    reactants and products of the reaction, drawn as chemical structures (via the
    Ketcher structure editor) and laid out in a reaction worksheet table. Each row
    of that table is a reaction participant (a reactant or a product), and its
    quantities (mass, moles, equivalents, concentration) can be filled in.

    A synthesis always belongs to a block inside a Notebook (see
    [`NotebookCollection`][albert.collections.notebooks.NotebookCollection]); the parent notebook
    is supplied when the record is created. Synthesis records are referenced by
    their Synthesis ID (format ``SYN...``, e.g. ``"SYNA1"``).

    A typical flow is: [`create`][albert.collections.synthesis.SynthesisCollection.create] the record, draw the reaction and push the
    canvas with [`update_canvas_data`][albert.collections.synthesis.SynthesisCollection.update_canvas_data], initialize the reactant/product table
    with [`create_reactant_productant_table`][albert.collections.synthesis.SynthesisCollection.create_reactant_productant_table], then set per-row quantities with
    [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values].

    This collection is accessed as ``client.synthesis``.

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
        Get a single synthesis record by its ID.
    search(...) -> Iterator[SynthesisSearchItem]
        Search for synthesis records matching the given filters, returning lightweight hits.
    update(synthesis) -> Synthesis
        Update an existing synthesis record.
    update_canvas_data(synthesis_id, smiles, data, png) -> Synthesis
        Replace the drawn reaction (SMILES, canvas data, and preview image).
    update_reactant_row_values(synthesis_id, row_id, values) -> Synthesis
        Set the quantities (mass, moles, eq, concentration) for one reactant row.
    create_reactant_productant_table(synthesis_id) -> Synthesis
        Initialize the reactant/product table and reveal the reaction worksheet.
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
        is empty; draw the reaction and push it with [`update_canvas_data`][albert.collections.synthesis.SynthesisCollection.update_canvas_data], and
        build out the reactant/product table with
        [`create_reactant_productant_table`][albert.collections.synthesis.SynthesisCollection.create_reactant_productant_table].

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
        """Get a synthesis record by its ID.

        !!! example
            ```python
            synthesis = client.synthesis.get_by_id(id="SYNA1")
            print(synthesis.name)
            ```

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
            The fully populated synthesis record.
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
    def search(
        self,
        *,
        text: str | None = None,
        created_by: str | list[str] | None = None,
        created_by_name: str | list[str] | None = None,
        smiles: str | list[str] | None = None,
        product_created: str | list[str] | None = None,
        chemical_name: str | list[str] | None = None,
        cas: str | list[str] | None = None,
        reactant_name: str | list[str] | None = None,
        reactant_cas: str | list[str] | None = None,
        product_name: str | list[str] | None = None,
        product_cas: str | list[str] | None = None,
        project_id: str | list[str] | None = None,
        inventory_id: str | list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        source_field: str | list[str] | None = None,
        sort_by: str | None = None,
        order: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[SynthesisSearchItem]:
        """Search for synthesis records matching the given filters.

        Returns lightweight
        [`SynthesisSearchItem`][albert.resources.synthesis.SynthesisSearchItem] hits, best for
        free-text lookups and pulling IDs. Results are returned as a lazily paginated
        iterator. Pass a hit's ID to
        [`get_by_id`][albert.collections.synthesis.SynthesisCollection.get_by_id] to fetch the
        fully populated [`Synthesis`][albert.resources.synthesis.Synthesis].

        !!! example
            ```python
            hits = client.synthesis.search(text="amide coupling", max_items=10)
            first = next(iter(hits))
            first.name
            # 'Amide coupling'
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against synthesis names and metadata.
        created_by : str or list[str], optional
            Filter by creator user ID(s).
        created_by_name : str or list[str], optional
            Filter by creator display name(s).
        smiles : str or list[str], optional
            Filter by SMILES structure(s).
        product_created : str or list[str], optional
            Filter by product-created flag(s).
        chemical_name : str or list[str], optional
            Filter by chemical name(s).
        cas : str or list[str], optional
            Filter by CAS number(s).
        reactant_name : str or list[str], optional
            Filter by reactant name(s).
        reactant_cas : str or list[str], optional
            Filter by reactant CAS number(s).
        product_name : str or list[str], optional
            Filter by product name(s).
        product_cas : str or list[str], optional
            Filter by product CAS number(s).
        project_id : str or list[str], optional
            Filter by Project ID(s) (format ``PRO...``).
        inventory_id : str or list[str], optional
            Filter by linked Inventory ID(s) (format ``INV...``).
        facet_text : str, optional
            Text to match within a facet search.
        facet_field : str, optional
            Field to search within for facet filtering.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        source_field : str or list[str], optional
            Restrict which fields are returned on each search hit.
        sort_by : str, optional
            Attribute to sort results by.
        order : OrderBy, optional
            The order in which to sort results (``asc`` or ``desc``).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[SynthesisSearchItem]
            A lazily paginated iterator of matching lightweight synthesis hits.
        """
        params: dict[str, Any] = {
            "text": text,
            "createdBy": ensure_list(created_by),
            "createdByName": ensure_list(created_by_name),
            "smiles": ensure_list(smiles),
            "productCreated": ensure_list(product_created),
            "chemicalName": ensure_list(chemical_name),
            "cas": ensure_list(cas),
            "reactantName": ensure_list(reactant_name),
            "reactantCas": ensure_list(reactant_cas),
            "productName": ensure_list(product_name),
            "productCas": ensure_list(product_cas),
            "projectId": ensure_list(project_id),
            "inventoryId": ensure_list(inventory_id),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "sourceField": ensure_list(source_field),
            "sortBy": sort_by,
            "order": order,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [SynthesisSearchItem.model_validate(x) for x in items],
        )

    @validate_call
    def update_canvas_data(
        self, *, synthesis_id: SynthesisId, smiles: str, data: str, png: str
    ) -> Synthesis:
        """Update the Ketcher canvas data for a synthesis record.

        Use this to save the drawn reaction after editing it in the structure
        editor. It replaces the reaction SMILES, the serialized canvas, and the
        rendered preview image together.

        !!! example
            ```python
            synthesis = client.synthesis.update_canvas_data(
                synthesis_id="SYNA1",
                smiles="CC(=O)O.CN>>CC(=O)NC",
                data=serialized_canvas,
                png=base64_png,
            )
            ```

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
        """Update an existing synthesis record.

        Fetch the record with [`get_by_id`][albert.collections.synthesis.SynthesisCollection.get_by_id], modify the updatable fields on the
        returned object, then pass it here. Only the fields listed in Notes are
        sent; other differences are ignored. If nothing changed, the existing
        record is returned unmodified.

        !!! example
            ```python
            synthesis = client.synthesis.get_by_id(id="SYNA1")
            synthesis.name = "Amide coupling (revised)"
            updated = client.synthesis.update(synthesis=synthesis)
            ```

        Parameters
        ----------
        synthesis : Synthesis
            The synthesis record containing updated fields. Its ``id`` must be set.

        Returns
        -------
        Synthesis
            The updated synthesis record.

        Raises
        ------
        AlbertException
            If the synthesis record is missing an ID.

        Notes
        -----
        The following fields can be updated: ``name``, ``status``,
        ``hide_reaction_worksheet``.
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
        [`ReactionParticipant`][albert.resources.synthesis.ReactionParticipant] has a ``row_id``)
        or from ``Synthesis.row_sequence.reactants``.

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
        [`update_canvas_data`][albert.collections.synthesis.SynthesisCollection.update_canvas_data]) and before setting per-row quantities with
        [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values].

        !!! example
            ```python
            synthesis = client.synthesis.create_reactant_productant_table(
                synthesis_id="SYNA1",
            )
            ```

        Parameters
        ----------
        synthesis_id : SynthesisId
            The Synthesis ID to initialize (format ``SYN...``).

        Returns
        -------
        Synthesis
            The synthesis record with its reactant/product table initialized.
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
