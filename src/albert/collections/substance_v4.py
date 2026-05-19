import json
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
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
    get_by_ids(...) -> list[SubstanceV4Info]
        Retrieves substances by CAS IDs, substance IDs, or external IDs.
    get_by_id(...) -> SubstanceV4Info
        Retrieves a single substance by CAS ID, substance ID, or external ID.
    search(...) -> Iterator[SubstanceV4SearchItem]
        Searches substances by keyword or advanced filters.
    create(substance) -> SubstanceV4CreateResult
        Creates a new substance record.
    update_metadata(id, current_metadata, updated_metadata) -> None
        Updates metadata fields on a substance by diffing current vs updated state.
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
    ) -> list[SubstanceV4Info]:
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
            Whether to suppress errors for unknown substances, by default None.
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
        list[SubstanceV4Info]
            The matching substances.
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
        return SubstanceV4Response.model_validate(response.json()).substances

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
    ) -> SubstanceV4Info:
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
            Whether to suppress errors for unknown substances, by default None.
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
        SubstanceV4Info
            The matching substance.
        """
        provided = sum([cas_id is not None, sub_id is not None, external_id is not None])
        if provided != 1:
            raise ValueError("Exactly one of cas_id, sub_id, or external_id must be provided.")

        results = self.get_by_ids(
            cas_ids=[cas_id] if cas_id else None,
            sub_ids=[sub_id] if sub_id else None,
            external_ids=[external_id] if external_id else None,
            region=region,
            catch_errors=catch_errors,
            language=language,
            classification_type=classification_type,
        )
        if not results:
            raise ValueError("No substance found for the provided identifier.")
        return results[0]

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
        current_metadata: SubstanceV4Metadata,
        updated_metadata: SubstanceV4Metadata,
    ) -> None:
        """Update metadata fields on a substance.

        Diffs ``current_metadata`` against ``updated_metadata`` and sends only the
        changed fields. Scalar fields support ``add`` and ``update``; custom tenant
        metadata fields also support ``delete`` (set the key to ``None`` in
        ``updated_metadata`` with a value in ``current_metadata``).

        Parameters
        ----------
        id : str
            The substance ID to update.
        current_metadata : SubstanceV4Metadata
            The current metadata state of the substance.
        updated_metadata : SubstanceV4Metadata
            The desired metadata state of the substance.

        Notes
        -----
        The following fields can be updated: ``notes``, ``description``, ``cas_smiles``,
        ``inchi_key``, ``iupac_name``, ``cactus_status``, and any custom metadata fields
        configured for the tenant.
        """
        sub_id = id if id.startswith("SUB") else f"SUB{id}"
        operations = []

        for attr, wire_name in [
            ("notes", "notes"),
            ("description", "description"),
            ("cas_smiles", "casSmiles"),
            ("inchi_key", "inchiKey"),
            ("iupac_name", "iUpacName"),
            ("cactus_status", "cactusStatus"),
        ]:
            old = getattr(current_metadata, attr)
            new = getattr(updated_metadata, attr)
            if old == new:
                continue
            if old is None and new is not None:
                operations.append({"operation": "add", "attribute": wire_name, "newValue": new})
            elif old is not None and new is not None:
                operations.append(
                    {
                        "operation": "update",
                        "attribute": wire_name,
                        "oldValue": old,
                        "newValue": new,
                    }
                )
            # spec does not support delete for scalar fields — skip old→None case

        metadata_patches = self._generate_metadata_diff(
            existing_metadata=current_metadata.metadata or {},
            updated_metadata=updated_metadata.metadata or {},
        )
        operations.extend(
            p.model_dump(by_alias=True, mode="json", exclude_none=True) for p in metadata_patches
        )

        if not operations:
            return

        self.session.patch(f"{self.base_path}/metadata/{sub_id}", json={"data": operations})
