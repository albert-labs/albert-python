import json
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.types import _UNSET, MetadataItem, _UnsetType
from albert.resources.substance_v4 import (
    SubstanceV4Create,
    SubstanceV4CreateResult,
    SubstanceV4Info,
    SubstanceV4Metadata,
    SubstanceV4Response,
    SubstanceV4SearchItem,
)

_SEARCH_PAGE_SIZE = 20  # maximum page size accepted by the v4 search endpoint


class SubstanceV4SearchPaginator(AlbertPaginator):
    """Paginator for substance v4 search using integer offset pagination."""

    def __init__(
        self,
        *,
        path: str,
        session: AlbertSession,
        params: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        params = dict(params or {})
        self._offset = int(params.get("startKey", 0))
        params["startKey"] = self._offset
        params["limit"] = _SEARCH_PAGE_SIZE
        super().__init__(
            path=path,
            mode=PaginationMode.OFFSET,
            session=session,
            deserialize=lambda items: [SubstanceV4SearchItem.model_validate(i) for i in items],
            params=params,
            max_items=max_items,
        )

    def _create_iterator(self) -> Iterator[SubstanceV4SearchItem]:
        """Yield paginated search items."""
        yielded = 0
        while True:
            response = self._request()
            items = response.json().get("substances", [])

            if not items:
                return

            for item in self.deserialize(items):
                yield item
                yielded += 1
                if self.max_items is not None and yielded >= self.max_items:
                    return

            self._offset += len(items)
            self.params["startKey"] = self._offset


class SubstanceV4Collection(BaseCollection):
    """SubstanceV4Collection manages substance entities in the Albert platform (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for substance API requests.

    Methods
    -------
    get_by_ids(...) -> SubstanceV4Response
        Retrieves substances by CAS IDs, substance IDs, or external IDs.
    get_by_id(...) -> SubstanceV4Info | None
        Retrieves a single substance by CAS ID, substance ID, or external ID.
    search(...) -> Iterator[SubstanceV4SearchItem]
        Searches substances by keyword or advanced filters.
    create(substance) -> SubstanceV4CreateResult
        Creates a new substance record.
    update_metadata(id, ...) -> None
        Updates metadata fields on a substance.
    """

    _api_version = "v4"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{SubstanceV4Collection._api_version}/substances"

    @validate_call
    def get_by_ids(
        self,
        *,
        cas_ids: list[str] | None = None,
        sub_ids: list[str] | None = None,
        external_ids: list[str] | None = None,
        region: str = "global",
        catch_errors: bool | None = None,
        language: str | None = None,
        classification_type: str | None = None,
    ) -> SubstanceV4Response:
        """Retrieve substances by their identifiers.

        At least one of ``cas_ids``, ``sub_ids``, or ``external_ids`` must be provided.

        Parameters
        ----------
        cas_ids : list[str] | None
            CAS numbers to look up.
        sub_ids : list[str] | None
            Substance IDs to look up.
        external_ids : list[str] | None
            External IDs to look up.
        region : str, optional
            Region for hazard data. Common values: ``"global"``, ``"EU"``, ``"US"``,
            ``"UK"``. Defaults to ``"global"``.
        catch_errors : bool | None, optional
            When ``False``, substances with incomplete hazard data are still
            returned alongside any per-substance errors. When ``True`` or omitted,
            the request fails if any substance has incomplete hazard data.
            Does not affect whether not-found identifiers are included in the
            results. By default ``None``.
        language : str | None, optional
            BCP-47 language code for name translation (e.g. ``"EN"``, ``"DE"``,
            ``"FR"``), by default None.
        classification_type : str | None, optional
            Filter by classification type. Accepted values: ``"HARMONISED"``,
            ``"NOTIFIED"``, ``"SELF_CLASSIFIED"``; or their display labels
            ``"Harmonised C&L"``, ``"Notified C&L"``, ``"Self Classified"``,
            by default None.

        Returns
        -------
        SubstanceV4Response
            The matching substances and any per-substance retrieval errors.
        """
        if not any([cas_ids, sub_ids, external_ids]):
            raise ValueError("At least one of cas_ids, sub_ids, or external_ids must be provided.")

        params: dict = {"region": region}
        if cas_ids:
            params["casIDs"] = ",".join(cas_ids)
        if sub_ids:
            params["subIDs"] = ",".join(sub_ids)
        if external_ids:
            params["externalIDs"] = ",".join(external_ids)
        if catch_errors is not None:
            params["catchErrors"] = json.dumps(catch_errors)
        if language:
            params["language"] = language
        if classification_type:
            params["classificationType"] = classification_type

        response = self.session.get(self.base_path, params=params)
        return SubstanceV4Response.model_validate(response.json())

    @validate_call
    def get_by_id(
        self,
        *,
        cas_id: str | None = None,
        sub_id: str | None = None,
        external_id: str | None = None,
        region: str = "global",
        catch_errors: bool | None = None,
        language: str | None = None,
        classification_type: str | None = None,
    ) -> SubstanceV4Info | None:
        """Retrieve a single substance by its identifier.

        Provide exactly one of ``cas_id``, ``sub_id``, or ``external_id``.

        Parameters
        ----------
        cas_id : str | None
            The CAS number.
        sub_id : str | None
            The substance ID.
        external_id : str | None
            The external ID.
        region : str, optional
            Region for hazard data. Common values: ``"global"``, ``"EU"``, ``"US"``,
            ``"UK"``. Defaults to ``"global"``.
        catch_errors : bool | None, optional
            When ``False``, substances with incomplete hazard data are still
            returned alongside any per-substance errors. When ``True`` or omitted,
            the request fails if any substance has incomplete hazard data.
            Does not affect whether not-found identifiers are included in the
            results. By default ``None``.
        language : str | None, optional
            BCP-47 language code for name translation (e.g. ``"EN"``, ``"DE"``,
            ``"FR"``), by default None.
        classification_type : str | None, optional
            Filter by classification type. Accepted values: ``"HARMONISED"``,
            ``"NOTIFIED"``, ``"SELF_CLASSIFIED"``; or their display labels
            ``"Harmonised C&L"``, ``"Notified C&L"``, ``"Self Classified"``,
            by default None.

        Returns
        -------
        SubstanceV4Info | None
            The matching substance, or ``None`` if not found.
        """
        provided = sum([cas_id is not None, sub_id is not None, external_id is not None])
        if provided != 1:
            raise ValueError("Exactly one of cas_id, sub_id, or external_id must be provided.")

        response = self.get_by_ids(
            cas_ids=[cas_id] if cas_id else None,
            sub_ids=[sub_id] if sub_id else None,
            external_ids=[external_id] if external_id else None,
            region=region,
            catch_errors=catch_errors,
            language=language,
            classification_type=classification_type,
        )
        if not response.substances:
            return None
        return response.substances[0]

    @validate_call
    def search(
        self,
        *,
        search_key: str | None = None,
        cas: str | None = None,
        ec: str | None = None,
        name: str | None = None,
        region: str = "global",
        classification_type: str | None = None,
        start_key: int = 0,
        max_items: int = 100,
    ) -> Iterator[SubstanceV4SearchItem]:
        """Search for substances by keyword or advanced filters.

        At least one of ``search_key``, ``cas``, ``ec``, or ``name`` must be provided.
        If both ``search_key`` and advanced filters are provided, the advanced filters
        take precedence.

        Parameters
        ----------
        search_key : str | None
            Free-text search term.
        cas : str | None
            Filter by CAS identifier.
        ec : str | None
            Filter by EC identifier.
        name : str | None
            Filter by substance name.
        region : str, optional
            Region for hazard data. Common values: ``"global"``, ``"EU"``, ``"US"``,
            ``"UK"``. Defaults to ``"global"``.
        classification_type : str | None, optional
            Filter by classification type. Accepted values: ``"HARMONISED"``,
            ``"NOTIFIED"``, ``"SELF_CLASSIFIED"``; or their display labels
            ``"Harmonised C&L"``, ``"Notified C&L"``, ``"Self Classified"``,
            by default None.
        start_key : int, optional
            Offset to resume pagination from, by default 0.
        max_items : int, optional
            Maximum number of items to yield, by default 100.

        Yields
        ------
        SubstanceV4SearchItem
            Matching substance search records.
        """
        if not any([search_key, cas, ec, name]):
            raise ValueError("At least one of search_key, cas, ec, or name must be provided.")

        params: dict = {"region": region, "startKey": start_key}
        if search_key:
            params["searchKey"] = search_key
        if cas:
            params["cas"] = cas
        if ec:
            params["ec"] = ec
        if name:
            params["name"] = name
        if classification_type:
            params["classificationType"] = classification_type

        yield from SubstanceV4SearchPaginator(
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
        )

    @validate_call
    def create(self, *, substance: SubstanceV4Create) -> SubstanceV4CreateResult:
        """Create a new substance record.

        Parameters
        ----------
        substance : SubstanceV4Create
            The substance data to create.

        Returns
        -------
        SubstanceV4CreateResult
            The result containing created, failed, and existing items.
        """
        payload = [substance.model_dump(by_alias=True, mode="json", exclude_none=True)]
        response = self.session.post(self.base_path, json=payload)
        return SubstanceV4CreateResult.model_validate(response.json())

    @validate_call
    def update_metadata(
        self,
        *,
        id: str,
        notes: str | _UnsetType = _UNSET,
        description: str | _UnsetType = _UNSET,
        cas_smiles: str | _UnsetType = _UNSET,
        inchi_key: str | _UnsetType = _UNSET,
        iupac_name: str | _UnsetType = _UNSET,
        cactus_status: str | _UnsetType = _UNSET,
        metadata: dict[str, MetadataItem | None] | _UnsetType = _UNSET,
    ) -> None:
        """Update metadata fields on a substance.

        Only the keyword arguments you pass are updated — all others are left unchanged.
        The current state is fetched automatically.

        Parameters
        ----------
        id : str
            The substance ID to update.
        notes : str, optional
            Free-text notes.
        description : str, optional
            Substance description.
        cas_smiles : str, optional
            SMILES notation for the structure.
        inchi_key : str, optional
            InChIKey identifier.
        iupac_name : str, optional
            IUPAC name.
        cactus_status : str, optional
            CACTUS resolver status.
        metadata : dict[str, MetadataItem | None], optional
            Custom tenant metadata fields to update. Only the keys listed in this dict
            are touched; all other custom fields on the substance are left unchanged.

            Value types by field kind:

            - **String / number fields** — pass the value directly (``"5 mg/mL"``, ``42``).
            - **Single-select fields** — pass an ``EntityLink``; use
              ``client.lists.get_matching_item()`` to look up the ID.
            - **Multi-select fields** — pass a list of ``EntityLink`` objects; only the
              changed items are sent.
            - **Delete a field** — pass ``None`` as the value (works for all field types).

        Notes
        -----
        The following fields can be updated: ``notes``, ``description``, ``cas_smiles``,
        ``inchi_key``, ``iupac_name``, ``cactus_status``, and any custom metadata fields
        configured for the tenant.

        Examples
        --------
        Update a scalar field and a custom string field:

            client.substances_v4.update_metadata(
                id="SUB123",
                notes="new notes",
                metadata={"solubility": "5 mg/mL"},
            )

        Set a single-select custom field:

            client.substances_v4.update_metadata(
                id="SUB123",
                metadata={"cmr_eu": EntityLink(id="LST1253")},
            )

        Update a multi-select custom field (becomes exactly this set):

            client.substances_v4.update_metadata(
                id="SUB123",
                metadata={"amide_category": [EntityLink(id="LST1256"), EntityLink(id="LST1257")]},
            )

        Delete a custom field:

            client.substances_v4.update_metadata(id="SUB123", metadata={"old_key": None})
        """
        scalar_kwargs = {
            "notes": notes,
            "description": description,
            "cas_smiles": cas_smiles,
            "inchi_key": inchi_key,
            "iupac_name": iupac_name,
            "cactus_status": cactus_status,
        }
        if all(v is _UNSET for v in scalar_kwargs.values()) and metadata is _UNSET:
            return

        sub_id = id if id.startswith("SUB") else f"SUB{id}"
        response = self.get_by_ids(sub_ids=[sub_id], catch_errors=False)
        substance = response.substances[0] if response.substances else None
        operations = []

        for attr, wire_name in [
            ("notes", "notes"),
            ("description", "description"),
            ("cas_smiles", "casSmiles"),
            ("inchi_key", "inchiKey"),
            ("iupac_name", "iUpacName"),
            ("cactus_status", "cactusStatus"),
        ]:
            new = scalar_kwargs[attr]
            if new is _UNSET:
                continue
            old = getattr(substance, attr, None) if substance is not None else None
            if old == new:
                continue
            if old is None:
                operations.append({"operation": "add", "attribute": wire_name, "newValue": new})
            else:
                operations.append(
                    {
                        "operation": "update",
                        "attribute": wire_name,
                        "oldValue": old,
                        "newValue": new,
                    }
                )

        if metadata is not _UNSET and metadata:
            # Coerce raw JSON dicts to EntityLink objects so _generate_metadata_diff
            # can call .id on single/multi-select values.
            raw_meta = substance.metadata if substance is not None else {}
            coerced = SubstanceV4Metadata.model_validate({"metadata": raw_meta or {}})
            current_meta = coerced.metadata or {}
            relevant_existing = {k: v for k, v in current_meta.items() if k in metadata}
            non_null_updates = {k: v for k, v in metadata.items() if v is not None}
            metadata_patches = self._generate_metadata_diff(
                existing_metadata=relevant_existing,
                updated_metadata=non_null_updates,
            )
            operations.extend(
                p.model_dump(by_alias=True, mode="json", exclude_none=True)
                for p in metadata_patches
            )

        if not operations:
            return

        self.session.patch(f"{self.base_path}/metadata/{sub_id}", json={"data": operations})
