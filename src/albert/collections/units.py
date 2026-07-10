import logging
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import UnitId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.utils import ensure_list
from albert.resources.units import Unit, UnitCategory


class UnitCollection(BaseCollection):
    """Manage Units of measure in the Albert platform.

    A Unit is a unit of measure (e.g. ``g``, ``mL``, ``°C``). Units are referenced
    throughout the platform: they qualify inventory quantities, parameter values,
    and property results. Each unit has a name, an optional display symbol, an
    optional list of synonyms (alternate spellings), and a category
    (:class:`~albert.resources.units.UnitCategory`, e.g. ``Mass`` or ``Volume``).

    Units are referenced by their Unit ID (format ``UNI...``, e.g. ``"UNI1"``).

    This collection is accessed as ``client.units``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for unit requests.

    Methods
    -------
    create(unit) -> Unit
        Register a new unit.
    get_or_create(unit) -> Unit
        Return the existing unit matching the name, or create it.
    get_by_id(id) -> Unit
        Retrieve a single unit by its Unit ID.
    get_by_ids(ids) -> list[Unit]
        Retrieve many units by ID in batches.
    get_by_name(name, exact_match=False) -> Unit | None
        Retrieve a unit by name, or None if not found.
    get_all(...) -> Iterator[Unit]
        Iterate over units with optional filters.
    update(unit) -> Unit
        Apply changes to an existing unit.
    delete(id) -> None
        Delete a unit by its Unit ID.
    exists(name, exact_match=True) -> bool
        Check whether a unit with the given name exists.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        unit = client.units.get_by_id(id="UNI1")
        print(unit.name, unit.symbol, unit.category)
        ```
    """

    _updatable_attributes = {"symbol", "synonyms", "category"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the UnitCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnitCollection._api_version}/units"

    def create(self, *, unit: Unit) -> Unit:
        """Register a new unit.

        Parameters
        ----------
        unit : Unit
            The unit to create.

        Returns
        -------
        Unit
            The newly created unit, including its assigned Unit ID.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.units import Unit, UnitCategory
            unit = client.units.create(
                unit=Unit(name="milligram", symbol="mg", category=UnitCategory.MASS)
            )
            ```
        """
        response = self.session.post(
            self.base_path, json=unit.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        unit = Unit(**response.json())
        return unit

    def get_or_create(self, *, unit: Unit) -> Unit:
        """Return the existing unit matching the given name, or create it.

        Looks for an existing unit with the same name (exact match). If one is
        found it is returned unchanged; otherwise a new unit is created.

        Parameters
        ----------
        unit : Unit
            The unit to find or create.

        Returns
        -------
        Unit
            The existing or newly created unit.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.units import Unit, UnitCategory
            unit = client.units.get_or_create(
                unit=Unit(name="gram", symbol="g", category=UnitCategory.MASS)
            )
            ```
        """
        match = self.get_by_name(name=unit.name, exact_match=True)
        if match:
            logging.warning(
                f"Unit with the name {unit.name} already exists. Returning the existing unit."
            )
            return match
        return self.create(unit=unit)

    @validate_call
    def get_by_id(self, *, id: UnitId) -> Unit:
        """Retrieve a single unit by its Unit ID.

        Parameters
        ----------
        id : UnitId
            The Unit ID to retrieve (format ``UNI...``).

        Returns
        -------
        Unit
            The matching unit.

        Examples
        --------
        !!! example
            ```python
            unit = client.units.get_by_id(id="UNI1")
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        this_unit = Unit(**response.json())
        return this_unit

    @validate_call
    def get_by_ids(self, *, ids: list[UnitId]) -> list[Unit]:
        """Retrieve many units by their IDs.

        IDs are fetched in batches, so arbitrarily long lists are supported.

        Parameters
        ----------
        ids : list[UnitId]
            The Unit IDs to retrieve.

        Returns
        -------
        list[Unit]
            The matching units. Units not found are omitted.

        Examples
        --------
        !!! example
            ```python
            units = client.units.get_by_ids(ids=["UNI1", "UNI2"])
            ```
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 500] for i in range(0, len(ids), 500)]
        return [
            Unit(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    @validate_call
    def update(self, *, unit: Unit) -> Unit:
        """Apply changes to an existing unit.

        Fetch a unit (e.g. via :meth:`get_by_id`), modify the updatable fields on
        the returned object, then pass it here. The unit is matched by its ``id``.

        Parameters
        ----------
        unit : Unit
            The unit carrying the desired changes. Must have its ``id`` set.

        Returns
        -------
        Unit
            The updated unit, re-fetched from Albert.

        Notes
        -----
        The following fields can be updated: ``category``, ``symbol``, ``synonyms``.

        Examples
        --------
        !!! example
            ```python
            unit = client.units.get_by_id(id="UNI1")
            unit.symbol = "g"
            unit.synonyms = ["gram", "grams"]
            updated = client.units.update(unit=unit)
            ```
        """
        unit_id = unit.id
        original_unit = self.get_by_id(id=unit_id)
        payload = self._generate_unit_patch_payload(existing=original_unit, updated=unit)
        url = f"{self.base_path}/{unit_id}"

        # The backend rejects more than one operation on the same attribute in a
        # single request, so each Synonyms edit is sent as its own request.
        synonym_data = [d for d in payload.data if d.attribute == "Synonyms"]
        other_data = [d for d in payload.data if d.attribute != "Synonyms"]
        batches = [other_data] if other_data else []
        batches.extend([datum] for datum in synonym_data)
        for batch in batches:
            self.session.patch(
                url, json=PatchPayload(data=batch).model_dump(mode="json", by_alias=True)
            )

        unit = self.get_by_id(id=unit_id)
        return unit

    def _generate_unit_patch_payload(self, *, existing: Unit, updated: Unit) -> PatchPayload:
        """Generate patch request data for a unit, handling synonyms as item-level edits."""
        payload = self._generate_patch_payload(existing=existing, updated=updated)

        # Synonyms are added/removed one at a time; there is no list-level update,
        # so replace any whole-list datum with per-item add/delete operations.
        payload.data = [d for d in payload.data if d.attribute != "Synonyms"]
        if "synonyms" not in updated.model_fields_set:
            return payload
        existing_synonyms = existing.synonyms or []
        updated_synonyms = updated.synonyms or []
        payload.data.extend(
            PatchDatum(attribute="Synonyms", operation=PatchOperation.ADD, new_value=synonym)
            for synonym in updated_synonyms
            if synonym not in existing_synonyms
        )
        payload.data.extend(
            PatchDatum(attribute="Synonyms", operation=PatchOperation.DELETE, new_value=synonym)
            for synonym in existing_synonyms
            if synonym not in updated_synonyms
        )
        return payload

    @validate_call
    def delete(self, *, id: UnitId) -> None:
        """Delete a unit by its Unit ID.

        Parameters
        ----------
        id : UnitId
            The Unit ID to delete.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.units.delete(id="UNI1")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def get_all(
        self,
        *,
        name: str | list[str] | None = None,
        category: UnitCategory | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        exact_match: bool = False,
        verified: bool | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Unit]:
        """Iterate over units, with optional filters.

        Results are fetched page by page as you iterate, so this scales to large
        result sets without loading everything at once.

        Parameters
        ----------
        name : str or list[str], optional
            One or more unit names to filter by.
        category : UnitCategory, optional
            Restrict results to a single unit category (e.g. ``Mass``, ``Volume``).
        order_by : OrderBy, optional
            Sort direction for results. Defaults to ``OrderBy.DESCENDING``.
        exact_match : bool, optional
            Whether ``name`` must match exactly. Defaults to False (substring match).
        verified : bool, optional
            Filter by whether the unit is verified. Defaults to None (no filter).
        start_key : str, optional
            Pagination key to resume iteration from a previous position.
        max_items : int, optional
            Maximum number of units to return in total. If None, iterates over all
            matching units.

        Returns
        -------
        Iterator[Unit]
            An iterator over the matching units.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.units import UnitCategory
            for unit in client.units.get_all(category=UnitCategory.MASS, max_items=50):
                print(unit.name, unit.symbol)
            ```
        """
        params = {
            "orderBy": order_by,
            "name": ensure_list(name),
            "exactMatch": exact_match,
            "verified": verified,
            "category": category,
            "startKey": start_key,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Unit(**item) for item in items],
        )

    def get_by_name(self, *, name: str, exact_match: bool = False) -> Unit | None:
        """Retrieve a unit by its name.

        Parameters
        ----------
        name : str
            The unit name to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default False.

        Returns
        -------
        Unit or None
            The matching unit, or None if no unit with that name exists.

        Examples
        --------
        !!! example
            ```python
            unit = client.units.get_by_name(name="gram", exact_match=True)
            ```
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=10)
        # return the first with exactly that name
        for unit in found:
            if unit.name == name:
                return unit
        return None

    def exists(self, *, name: str, exact_match: bool = True) -> bool:
        """Check whether a unit with the given name exists.

        Parameters
        ----------
        name : str
            The unit name to check.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        bool
            True if a matching unit exists, False otherwise.

        Examples
        --------
        !!! example
            ```python
            if client.units.exists(name="gram"):
                print("gram is defined")
            ```
        """
        return self.get_by_name(name=name, exact_match=exact_match) is not None
