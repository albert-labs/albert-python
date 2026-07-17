import re
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.lists import ListsCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import CasId
from albert.core.shared.models.base import EntityLink
from albert.resources.cas import Cas


class CasPaginator(AlbertPaginator):
    """Paginator for CAS filtered search using self-managed integer offset pagination."""

    def __init__(
        self,
        *,
        path: str,
        session: AlbertSession,
        params: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        params = dict(params or {})
        params["startKey"] = self._cas_offset = int(params.get("startKey", 0))
        params["limit"] = 50
        super().__init__(
            path=path,
            mode=PaginationMode.OFFSET,
            session=session,
            deserialize=lambda items: [Cas(**item) for item in items],
            params=params,
            max_items=max_items,
        )

    def _update_params(self, *, data: dict[str, Any], count: int) -> bool:
        self._cas_offset += count
        self.params["startKey"] = self._cas_offset
        return True


class CasCollection(BaseCollection):
    """Manage CAS entries in the Albert platform.

    A CAS entry ([`Cas`][albert.resources.cas.Cas]) records a chemical substance
    identified by its CAS Registry Number (e.g. ``"7727-37-9"`` for nitrogen). CAS
    entries are the shared chemical dictionary that raw-material Inventory Items
    point to: a raw material lists the CAS numbers of its constituents, each paired
    with an amount (see [`CasAmount`][albert.resources.inventory.CasAmount]).

    CAS entries are referenced by their CAS ID (format ``CAS...``, e.g. ``"CAS1"``).
    Most workflows either look a substance up by its registry number
    ([`get_by_number`][albert.collections.cas.CasCollection.get_by_number]) or ensure one exists before linking it
    ([`get_or_create`][albert.collections.cas.CasCollection.get_or_create]).

    This collection is accessed as ``client.cas``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        cas = client.cas.get_or_create(cas="7727-37-9")
        print(cas.id, cas.number)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for CAS requests.

    Methods
    -------
    create(cas) -> Cas
        Create a new CAS entry from a registry number or Cas object.
    get_or_create(cas) -> Cas
        Return the existing entry for a registry number, or create it.
    get_by_id(id) -> Cas
        Get a single CAS entry by its ID.
    get_by_number(number, exact_match=True) -> Cas | None
        Get a CAS entry by its registry number.
    get_all(...) -> Iterator[Cas]
        Iterate over CAS entries, optionally filtered by number(s) or ID.
    exists(number, exact_match=True) -> bool
        Check whether a CAS entry with the given number exists.
    update(updated_object) -> Cas
        Update an existing CAS entry.
    delete(id) -> None
        Delete a CAS entry by its ID.
    """

    _updatable_attributes = {"notes", "description", "smiles", "metadata"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a CasCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CasCollection._api_version}/cas"

    # CAS list-type metadata is a special case. The CAS API expects entity-link
    # objects ({"id", "name"}) and stores bare list IDs literally, unlike inventory
    # and other services that normalize IDs on write. create() and update() therefore
    # hydrate omitted names via lists.get_by_id before sending list metadata payloads.

    def _list_metadata_link_payload(self, link: EntityLink) -> dict[str, str]:
        """Build a list metadata entity-link payload, hydrating name when omitted."""
        name = link.name or ListsCollection(session=self.session).get_by_id(id=link.id).name
        return {"id": link.id, "name": name}

    def _metadata_list_patch_value(self, links: list[EntityLink], *, as_list: bool = False) -> Any:
        """Serialize CAS list metadata for PATCH as entity-link objects."""
        payloads = [self._list_metadata_link_payload(link) for link in links]
        if as_list:
            return payloads
        return payloads[0] if len(payloads) == 1 else payloads

    @validate_call
    def get_all(
        self,
        *,
        number: str | None = None,
        cas: list[str] | None = None,
        id: CasId | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | int | None = None,
        max_items: int | None = None,
    ) -> Iterator[Cas]:
        """Iterate over CAS entries, optionally filtered.

        Use this to list CAS entries or to search by one or more registry numbers.
        Results are streamed page by page, so you can iterate large result sets
        without loading everything at once. To fetch a single entry when you
        already know its registry number or CAS ID, prefer [`get_by_number`][albert.collections.cas.CasCollection.get_by_number]
        or [`get_by_id`][albert.collections.cas.CasCollection.get_by_id].

        !!! example
            ```python
            # List the most recent CAS entries
            for cas in client.cas.get_all(max_items=10):
                print(cas.id, cas.number)

            # Look up specific registry numbers
            matches = list(client.cas.get_all(cas=["7727-37-9", "64-17-5"]))
            ```

        Parameters
        ----------
        number : str, optional
            Filter by a single CAS registry number (substring/partial match).
        cas : list[str], optional
            Filter by an exact list of CAS registry numbers.
        id : CasId, optional
            Return only the entry with this CAS ID (format ``CAS...``). When set,
            other filters are ignored and at most one entry is yielded.
        order_by : OrderBy, optional
            Sort direction. Defaults to ``OrderBy.DESCENDING``.
        start_key : str or int, optional
            Pagination resume key. For unfiltered listing, pass the string key
            returned by a previous page. For filtered search (``number`` or
            ``cas``), pass an integer offset.
        max_items : int, optional
            Maximum number of entries to yield in total. If None, iterates over
            all matching entries.

        Yields
        ------
        Cas
            Matching CAS entries.
        """

        params: dict[str, Any] = {"orderBy": order_by}
        if id is not None:
            yield self.get_by_id(id=id)
            return

        if number is not None or cas:
            # Filtered search path: self-managed integer offset pagination.
            # The backend has a bug where it overwrites the numeric lastKey with a
            # string key, we must ignore lastKey and use integer offsets. (TAS-564)
            start_offset = 0
            if start_key is not None:
                try:
                    start_offset = int(start_key)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "start_key must be an integer for filtered CAS search."
                    ) from exc
            params["startKey"] = start_offset
            if number is not None:
                params["number"] = number
            if cas:
                params["cas"] = cas
            yield from CasPaginator(
                path=self.base_path,
                session=self.session,
                params=params,
                max_items=max_items,
            )
        else:
            # Unfiltered listing path: string key pagination via lastKey in response.
            if start_key is not None:
                params["startKey"] = start_key
            yield from AlbertPaginator(
                mode=PaginationMode.KEY,
                path=self.base_path,
                session=self.session,
                params=params,
                max_items=max_items,
                deserialize=lambda items: [Cas(**item) for item in items],
            )

    @validate_call
    def exists(self, *, number: str, exact_match: bool = True, max_items: int | None = 50) -> bool:
        """Check whether a CAS entry exists for the given registry number.

        Useful before creating an entry to avoid duplicates. To retrieve the
        matching entry itself (rather than a boolean), use [`get_by_number`][albert.collections.cas.CasCollection.get_by_number];
        to fetch-or-create in one step, use [`get_or_create`][albert.collections.cas.CasCollection.get_or_create].

        !!! example
            ```python
            client.cas.exists(number="7727-37-9")
            # True
            ```

        Parameters
        ----------
        number : str
            The CAS registry number to check.
        exact_match : bool, optional
            When True (default), require an exact registry-number match. When
            False, treat ``number`` as a partial match.
        max_items : int, optional
            Maximum number of results to search through when ``exact_match`` is
            False. Defaults to 50 (one page). Pass ``None`` for unbounded search.

        Returns
        -------
        bool
            True if a matching CAS entry exists, False otherwise.
        """
        return (
            self.get_by_number(number=number, exact_match=exact_match, max_items=max_items)
            is not None
        )

    def create(self, *, cas: str | Cas) -> Cas:
        """Create a new CAS entry.

        Use this to add a substance to Albert's CAS dictionary. If you are not
        sure whether the substance already exists, prefer [`get_or_create`][albert.collections.cas.CasCollection.get_or_create],
        which avoids creating a duplicate.

        !!! example
            ```python
            cas = client.cas.create(cas="7727-37-9")
            cas.id
            # 'CAS1'
            ```

        Parameters
        ----------
        cas : str or Cas
            The CAS registry number, or a fully built
            [`Cas`][albert.resources.cas.Cas] object. A bare string is treated as
            the registry number.

        Returns
        -------
        Cas
            The newly created entry, populated with its assigned CAS ID.
        """
        if isinstance(cas, str):
            cas = Cas(number=cas)

        payload = cas.model_dump(by_alias=True, exclude_unset=True, mode="json")
        # See class comment: CAS list metadata requires hydrated entity-link objects.
        if "metadata" in cas.model_fields_set and cas.metadata:
            payload["Metadata"] = {
                key: (
                    [self._list_metadata_link_payload(link) for link in value]
                    if isinstance(value, list)
                    else self._list_metadata_link_payload(value)
                    if isinstance(value, EntityLink)
                    else value
                )
                for key, value in cas.metadata.items()
            }
        response = self.session.post(self.base_path, json=payload)
        cas = Cas(**response.json())
        return cas

    def get_or_create(self, *, cas: str | Cas) -> Cas:
        """Return the CAS entry for a registry number, creating it if needed.

        This is the safest way to obtain a CAS entry to link to a raw material:
        it looks up the registry number with an exact match and returns the
        existing entry if found, otherwise creates a new one via [`create`][albert.collections.cas.CasCollection.create].

        !!! example
            ```python
            cas = client.cas.get_or_create(cas="7727-37-9")
            cas.id
            # 'CAS1'
            ```

        Parameters
        ----------
        cas : str or Cas
            The CAS registry number, or a fully built
            [`Cas`][albert.resources.cas.Cas] object. A bare string is treated as
            the registry number.

        Returns
        -------
        Cas
            The existing or newly created entry.
        """
        if isinstance(cas, str):
            cas = Cas(number=cas)
        found = self.get_by_number(number=cas.number, exact_match=True)
        if found:
            return found
        else:
            return self.create(cas=cas)

    @validate_call
    def get_by_id(self, *, id: CasId) -> Cas:
        """Get a single CAS entry by its ID.

        To look a substance up by its registry number instead, use
        [`get_by_number`][albert.collections.cas.CasCollection.get_by_number].

        !!! example
            ```python
            cas = client.cas.get_by_id(id="CAS1")
            cas.number
            # '7727-37-9'
            ```

        Parameters
        ----------
        id : CasId
            The CAS ID to retrieve (format ``CAS...``, e.g. ``"CAS1"``).

        Returns
        -------
        Cas
            The fully populated CAS entry.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        cas = Cas(**response.json())
        return cas

    def _clean_cas_number(self, text: str):
        """
        Cleans up strings that start with a CAS-like number by removing excess spaces within the CAS number format.
        This function mimics how the Albert backend checks for matching CAS numbers.
        Parameters:
        - text: str, the input string to clean.

        Returns:
        - str, the cleaned string with corrected CAS number formatting.
        """

        # Regex pattern to match CAS numbers at the start of the string (e.g., "50  - 0 -0")
        pattern = r"^(\d+)\s*-\s*(\d+)\s*-\s*(\d+)"

        # Replace matched CAS number patterns with cleaned-up format
        cleaned_text = re.sub(pattern, r"\1-\2-\3", text)

        return cleaned_text

    @validate_call
    def get_by_number(
        self, *, number: str, exact_match: bool = True, max_items: int | None = 50
    ) -> Cas | None:
        """Get a CAS entry by its registry number.

        The number is normalized before matching (extra spaces around the dashes
        are removed), mirroring how the Albert backend compares CAS numbers. To
        fetch-or-create in one step, use [`get_or_create`][albert.collections.cas.CasCollection.get_or_create].

        !!! example
            ```python
            cas = client.cas.get_by_number(number="7727-37-9")
            cas.id if cas else "not found"
            # 'CAS1'
            ```

        Parameters
        ----------
        number : str
            The CAS registry number to retrieve.
        exact_match : bool, optional
            When True (default), return the entry whose registry number matches
            exactly. When False, return the first entry whose number contains
            ``number`` as a substring.
        max_items : int, optional
            Maximum number of results to search through when ``exact_match`` is
            False. Defaults to 50 (one page). Pass ``None`` for unbounded search.

        Returns
        -------
        Cas or None
            The matching CAS entry, or None if no match is found.
        """
        cleaned_number = self._clean_cas_number(number)

        if exact_match:
            for candidate in self.get_all(cas=[cleaned_number], max_items=1):
                if self._clean_cas_number(candidate.number) == cleaned_number:
                    return candidate
            return None

        for candidate in self.get_all(number=cleaned_number, max_items=max_items):
            if cleaned_number in self._clean_cas_number(candidate.number):
                return candidate
        return None

    @validate_call
    def delete(self, *, id: CasId) -> None:
        """Delete a CAS entry by its CAS ID.

        !!! example
            ```python
            client.cas.delete(id="CAS1")
            ```

        Parameters
        ----------
        id : CasId
            The CAS ID to delete (format ``CAS...``).

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def update(self, *, updated_object: Cas) -> Cas:
        """Update an existing CAS entry.

        Fetch the entry (e.g. with [`get_by_id`][albert.collections.cas.CasCollection.get_by_id] or [`get_by_number`][albert.collections.cas.CasCollection.get_by_number]),
        modify the updatable fields on the returned object, then pass it here. The
        entry is matched by its ``id``, so that field must be set.

        !!! example
            ```python
            cas = client.cas.get_by_id(id="CAS1")
            cas.notes = "Confirmed against supplier COA."
            updated = client.cas.update(updated_object=cas)
            ```

        Parameters
        ----------
        updated_object : Cas
            The modified CAS entry. Must carry the ``id`` of the entry to update.

        Returns
        -------
        Cas
            The updated entry as it appears in Albert after the change.

        Notes
        -----
        Only the following fields are updatable: ``description``, ``metadata``,
        ``notes``, ``smiles``. Changes to other fields are ignored.
        """
        # Fetch the current object state from the server or database
        existing_cas = self.get_by_id(id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(existing=existing_cas, updated=updated_object)
        if not patch_payload.data:
            return existing_cas
        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))

        updated_cas = self.get_by_id(id=updated_object.id)
        return updated_cas
