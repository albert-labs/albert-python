from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import (
    UnitFamilyV4Id,
    UnitV4Id,
    ensure_unit_family_v4_id,
    ensure_unit_v4_id,
)
from albert.resources.units_v4 import (
    UnitV4,
    UnitV4Compatible,
    UnitV4Lookup,
    UnitV4Origin,
    UnitV4Type,
)

_SEARCH_PAGE_SIZE = 100  # maximum page size accepted by the v4 units search endpoint
_CREATE_FIELDS = {
    "name",
    "description",
    "type",
    "symbol",
    "synonyms",
    "ref_unit",
    "ref_unit_exp",
    "ref_unit_value",
    "unit_families",
}
_MERGE_PATCH_HEADERS = {"Content-Type": "application/merge-patch+json"}


def _validate_unit_symbol(symbol: str | None, *, operation: str) -> None:
    if symbol is None or not symbol.strip():
        raise ValueError(f"The unit must have a non-empty symbol to be {operation}.")


class UnitV4Collection(BaseCollection):
    """Manage Units of measure in the Albert platform (🧪 Beta).

    A v4 unit is either *convertible* (Albert resolves its SI unit, SI value and unit
    families from a reference unit or expression) or *non-convertible* (linked to
    unit families directly). See [`UnitV4`][albert.resources.units_v4.UnitV4].

    This collection is accessed as ``client.units_v4``. The v3 ``client.units``
    collection continues to work unchanged.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert
        from albert.resources.units_v4 import UnitV4, UnitV4Type

        client = Albert()
        unit = client.units_v4.create(
            unit=UnitV4(name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE, ref_unit="g")
        )
        print(unit.id, unit.si_unit, [f.name for f in unit.unit_families])
        # UNI3643d5a5-32c1-43c3-9f3e-aea810d21fc9 kg ['Mass']
        ```

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
    create(unit) -> UnitV4
        Create a new unit.
    get_by_id(id) -> UnitV4
        Get a single unit by its ID.
    get_by_ids(ids) -> list[UnitV4]
        Get many units by their IDs.
    search(...) -> Iterator[UnitV4]
        Search for units matching the given filters.
    update(unit) -> UnitV4
        Update an existing unit.
    setup(unit, unit_family_id) -> UnitV4
        Set up a Custom (Legacy) unit.
    delete(id) -> None
        Delete a unit by its ID.
    lookup(symbol=..., name=...) -> UnitV4Lookup
        Check whether a unit symbol or name is already in use.
    get_compatible(symbol=..., expression=...) -> UnitV4Compatible
        Get the SI mapping and compatible unit families for a symbol or expression.
    """

    _api_version = "v4"

    def __init__(self, *, session: AlbertSession):
        """Initialize a UnitV4Collection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnitV4Collection._api_version}/master-data/units"

    @staticmethod
    def _generate_create_payload(*, unit: UnitV4) -> dict[str, Any]:
        _validate_unit_symbol(unit.symbol, operation="created")
        payload = unit.model_dump(
            by_alias=True, mode="json", exclude_none=True, include=_CREATE_FIELDS
        )
        if "unitFamilies" in payload:
            payload["unitFamilies"] = [family["id"] for family in payload["unitFamilies"]]
        return payload

    @validate_call
    def create(self, *, unit: UnitV4) -> UnitV4:
        """Create a new unit.

        For a convertible unit, provide ``ref_unit`` (a global unit symbol) or
        ``ref_unit_exp`` (a unit expression); Albert resolves the SI unit, SI value and
        unit families. For a non-convertible unit, provide ``unit_families`` by ID.

        !!! example
            ```python
            from albert.resources.units_v4 import UnitFamilyV4Ref, UnitV4, UnitV4Type

            grams = client.units_v4.create(
                unit=UnitV4(name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE, ref_unit="g")
            )
            batch = client.units_v4.create(
                unit=UnitV4(
                    name="Batch",
                    symbol="batch",
                    type=UnitV4Type.NON_CONVERTIBLE,
                    unit_families=[UnitFamilyV4Ref(id="UNF3")],
                )
            )
            ```

        Parameters
        ----------
        unit : UnitV4
            The unit to create. ``symbol`` must be non-empty. ``name`` and ``symbol`` must be
            unique within the tenant.

        Returns
        -------
        UnitV4
            The newly created unit, including its assigned ID and resolved SI fields.
        """
        payload = self._generate_create_payload(unit=unit)
        response = self.session.post(self.base_path, json=payload)
        return UnitV4(**response.json())

    @validate_call
    def get_by_id(self, *, id: UnitV4Id) -> UnitV4:
        """Get a single unit by its ID.

        !!! example
            ```python
            unit = client.units_v4.get_by_id(id="UNI3643d5a5-32c1-43c3-9f3e-aea810d21fc9")
            print(unit.symbol, unit.type)
            # g UnitV4Type.CONVERTIBLE
            ```

        Parameters
        ----------
        id : UnitV4Id
            The unit ID: a UUID (Albert-managed) or a ``UNI...`` ID (tenant-created).

        Returns
        -------
        UnitV4
            The fully populated unit.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        unit = UnitV4(**response.json())
        unit._etag = response.headers.get("ETag")
        unit._snapshot = unit.model_copy(deep=True)
        return unit

    @validate_call
    def get_by_ids(self, *, ids: list[UnitV4Id]) -> list[UnitV4]:
        """Get many units by their IDs.

        IDs are fetched in batches, so arbitrarily long lists are supported.

        !!! example
            ```python
            units = client.units_v4.get_by_ids(ids=["UNI1", "UNI2"])
            ```

        Parameters
        ----------
        ids : list[UnitV4Id]
            The unit IDs to retrieve.

        Returns
        -------
        list[UnitV4]
            The matching units. Units not found are omitted.
        """
        units: list[UnitV4] = []
        for start in range(0, len(ids), _SEARCH_PAGE_SIZE):
            batch = ids[start : start + _SEARCH_PAGE_SIZE]
            response = self.session.post(
                f"{self.base_path}/search", json={"id": batch, "limit": _SEARCH_PAGE_SIZE}
            )
            units.extend(UnitV4(**item) for item in response.json().get("items") or [])
        return units

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        status: Status | None = None,
        origin: list[UnitV4Origin] | None = None,
        type: list[UnitV4Type] | None = None,
        family_name: list[str] | None = None,
        created_by: list[str] | None = None,
        sort_by: str | None = None,
        order_by: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[UnitV4]:
        """Search for units matching the given filters.

        Results are fetched page by page as you iterate. Call with no filters to
        list every unit visible to the tenant, including Albert-managed units.

        !!! example
            ```python
            from albert.resources.units_v4 import UnitV4Type

            for unit in client.units_v4.search(
                text="gram", type=[UnitV4Type.CONVERTIBLE], family_name=["Mass"], max_items=20
            ):
                print(unit.name, unit.symbol)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text search across unit names, symbols and synonyms.
        status : Status, optional
            Restrict results to active or inactive units.
        origin : list[UnitV4Origin], optional
            Restrict results to the given origins (for example Albert-managed or custom).
        type : list[UnitV4Type], optional
            Restrict results to convertible and/or non-convertible units.
        family_name : list[str], optional
            Restrict results to units in the named unit families.
        created_by : list[str], optional
            Restrict results to units created by the given user IDs.
        sort_by : str, optional
            The field to sort by (for example ``"name"``).
        order_by : OrderBy, optional
            Sort direction. Defaults to the backend ordering.
        max_items : int, optional
            Maximum number of units to yield. Defaults to ``None`` (all results).

        Returns
        -------
        Iterator[UnitV4]
            A lazily paginated iterator of matching units.
        """
        payload = {
            "text": text,
            "status": status,
            "origin": origin,
            "type": type,
            "familyName": family_name,
            "createdBy": created_by,
            "sortBy": sort_by,
            "order": order_by,
            "limit": _SEARCH_PAGE_SIZE,
        }
        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            method="POST",
            json=payload,
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [UnitV4(**item) for item in items],
        )

    @validate_call
    def update(self, *, unit: UnitV4) -> UnitV4:
        """Update an existing unit.

        Fetch a unit (e.g. via [`get_by_id`][albert.collections.units_v4.UnitV4Collection.get_by_id]),
        modify the updatable fields on the returned object, then pass it here. The unit
        is matched by its ``id``. Only fields you changed since the read are updated;
        everything else is left unchanged. If another writer changes the unit between
        your read and this call, the update is rejected instead of overwriting their
        change.

        !!! example
            ```python
            unit = client.units_v4.get_by_id(id="UNI1")
            unit.description = "Grams, used for powders"
            unit.synonyms = ["g", "gram", "grams"]
            updated = client.units_v4.update(unit=unit)
            ```

        Parameters
        ----------
        unit : UnitV4
            The unit carrying the desired changes. Must have its ``id`` set and must have
            been fetched from Albert first.

        Returns
        -------
        UnitV4
            The updated unit.

        Raises
        ------
        ValueError
            If the unit has no ``id``, was not fetched first, has a different ``id`` from
            the fetched unit, or has no ``type``. Also raised for attempts to change the
            ``type`` or SI mapping of a set-up unit, or to change ``unit_families`` on a
            convertible unit.
        albert.exceptions.PreconditionFailedError
            If the unit was modified after it was fetched. Fetch it again and
            reapply the changes.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``, ``symbol``,
        ``synonyms``. Non-convertible units can also update ``unit_families``. The ``type``
        and SI mapping (``si_unit``, ``si_value``, ``ref_unit``, ``ref_unit_exp``,
        ``ref_unit_value``) are fixed once a unit is set up.

        A Custom (Legacy) unit with no ``type`` must be set up with
        [`setup`][albert.collections.units_v4.UnitV4Collection.setup] before it can be updated.
        """
        if unit.id is None:
            raise ValueError("The unit must have an id to be updated.")
        if unit._etag is None or unit._snapshot is None:
            raise ValueError(
                "Fetch the unit with get_by_id() before updating it, so changed "
                "fields can be detected and concurrent edits rejected."
            )
        self._validate_snapshot_id(
            current_id=unit.id, snapshot_id=unit._snapshot.id, resource_name="unit"
        )
        unit_id = ensure_unit_v4_id(unit.id)
        patch = self._generate_merge_patch(existing=unit._snapshot, updated=unit)
        if not patch:
            return unit
        headers = {**_MERGE_PATCH_HEADERS, "If-Match": unit._etag}
        response = self.session.patch(f"{self.base_path}/{unit_id}", json=patch, headers=headers)
        updated = UnitV4(**response.json())
        updated._etag = response.headers.get("ETag")
        updated._snapshot = updated.model_copy(deep=True)
        return updated

    @validate_call
    def setup(self, *, unit: UnitV4, unit_family_id: UnitFamilyV4Id) -> UnitV4:
        """Set up a Custom (Legacy) unit.

        Fetch a unit with no ``type``, set its ``type`` and other desired fields, then pass
        it here with the family to use for existing references to the unit. The returned unit
        can be changed again with
        [`update`][albert.collections.units_v4.UnitV4Collection.update].

        !!! example
            ```python
            from albert.resources.units_v4 import UnitV4Type

            legacy = client.units_v4.get_by_id(id="UNI1")
            legacy.type = UnitV4Type.CONVERTIBLE
            legacy.ref_unit = "g"
            set_up = client.units_v4.setup(unit=legacy, unit_family_id="UNF1")
            ```

        Parameters
        ----------
        unit : UnitV4
            The fetched Custom (Legacy) unit to set up. Its ``id``, ``name``, ``symbol``,
            and ``type`` are required. ``symbol`` must be non-empty.
        unit_family_id : UnitFamilyV4Id
            The family to associate with existing references to this unit. It must be one
            of the unit's families after setup.

        Returns
        -------
        UnitV4
            The set-up unit.

        Raises
        ------
        ValueError
            If the unit has no ``id``, ``symbol``, or ``type``, has a blank ``symbol``,
            was not fetched first, or has a different ``id`` from the fetched unit.
        albert.exceptions.PreconditionFailedError
            If the unit was modified after it was fetched. Fetch it again and reapply the
            setup changes.

        Notes
        -----
        For a convertible unit, provide ``ref_unit`` or ``ref_unit_exp``, with an optional
        ``ref_unit_value``. Albert resolves its families, and ``unit_family_id`` must identify
        one of them. For a non-convertible unit, provide ``unit_families`` including
        ``unit_family_id``. Reference fields do not apply to non-convertible units.

        A unit can be set up only once. Use
        [`update`][albert.collections.units_v4.UnitV4Collection.update] for later changes.
        """
        payload = self._generate_setup_payload(unit=unit, unit_family_id=unit_family_id)
        if unit._etag is None or unit._snapshot is None:
            raise ValueError(
                "Fetch the unit with get_by_id() before setting it up, so concurrent "
                "edits can be rejected."
            )
        self._validate_snapshot_id(
            current_id=unit.id, snapshot_id=unit._snapshot.id, resource_name="unit"
        )
        response = self.session.post(
            f"{self.base_path}/setup", json=payload, headers={"If-Match": unit._etag}
        )
        set_up = UnitV4(**response.json())
        set_up._etag = response.headers.get("ETag")
        set_up._snapshot = set_up.model_copy(deep=True)
        return set_up

    @staticmethod
    def _generate_setup_payload(*, unit: UnitV4, unit_family_id: UnitFamilyV4Id) -> dict[str, Any]:
        if unit.id is None:
            raise ValueError("The unit must have an id to be set up.")
        _validate_unit_symbol(unit.symbol, operation="set up")
        if unit.type is None:
            raise ValueError("The unit must have a type to be set up.")

        include = {"id", "name", "description", "type", "symbol", "synonyms"}
        if unit.type is UnitV4Type.CONVERTIBLE:
            include.update({"ref_unit", "ref_unit_exp", "ref_unit_value"})
        else:
            include.add("unit_families")
        payload = unit.model_dump(by_alias=True, mode="json", exclude_none=True, include=include)
        payload["id"] = ensure_unit_v4_id(unit.id)
        payload["unitFamilyId"] = ensure_unit_family_v4_id(unit_family_id)
        if "unitFamilies" in payload:
            payload["unitFamilies"] = [family["id"] for family in payload["unitFamilies"]]
        return payload

    @staticmethod
    def _generate_merge_patch(*, existing: UnitV4, updated: UnitV4) -> dict[str, Any]:
        """Build the set of changed, patchable fields between two units.

        Only attributes the caller explicitly set on ``updated`` participate; unset
        attributes leave the server value untouched.
        """
        if existing.type is None:
            raise ValueError(
                "A Custom (Legacy) unit with no type must be set up with setup() "
                "before it can be updated."
            )

        patch: dict[str, Any] = {}
        for attr in ("name", "description", "symbol", "synonyms"):
            if attr not in updated.model_fields_set:
                continue
            new_value = getattr(updated, attr)
            if new_value != getattr(existing, attr):
                patch[attr] = new_value

        if "type" in updated.model_fields_set and updated.type != existing.type:
            raise ValueError("type cannot be changed or cleared after a unit is set up.")

        for attr in ("ref_unit", "ref_unit_exp", "ref_unit_value"):
            if attr not in updated.model_fields_set:
                continue
            if getattr(updated, attr) != getattr(existing, attr):
                raise ValueError(
                    "The SI mapping cannot be changed after a unit is set up; "
                    f"create a new unit instead of changing {attr}."
                )

        if "unit_families" in updated.model_fields_set:
            new_ids = [family.id for family in updated.unit_families or []]
            old_ids = [family.id for family in existing.unit_families or []]
            if sorted(new_ids) != sorted(old_ids):
                if existing.type is not UnitV4Type.NON_CONVERTIBLE:
                    raise ValueError(
                        "unit_families can only be changed on non-convertible units; "
                        "families of a convertible unit are derived from its SI mapping."
                    )
                patch["unitFamilies"] = new_ids
        return patch

    @validate_call
    def delete(self, *, id: UnitV4Id) -> None:
        """Delete a unit by its ID.

        The unit is deactivated rather than removed, and its name and symbol become
        available for reuse.

        !!! example
            ```python
            client.units_v4.delete(id="UNI1")
            ```

        Parameters
        ----------
        id : UnitV4Id
            The unit ID to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def lookup(self, *, symbol: str | None = None, name: str | None = None) -> UnitV4Lookup:
        """Check whether a unit symbol or name is already in use.

        Provide exactly one of ``symbol`` or ``name``. A symbol lookup also returns
        units whose symbol matches ignoring case (for example ``MPa`` and ``mPa``), so
        you can warn before creating a confusingly similar unit.

        !!! example
            ```python
            result = client.units_v4.lookup(symbol="MPa")
            if result.exists:
                print("MPa is taken")
            for unit in result.similar_matches:
                print(unit.symbol, unit.name)
            ```

        Parameters
        ----------
        symbol : str, optional
            The unit symbol to check (exact, case-sensitive match).
        name : str, optional
            The unit name to check (exact match).

        Returns
        -------
        UnitV4Lookup
            Whether an exact match exists, plus any similar units.
        """
        if (symbol is None) == (name is None):
            raise ValueError("Exactly one of symbol or name must be provided.")
        params = {"attr": "symbol", "value": symbol} if symbol is not None else {}
        if name is not None:
            params = {"attr": "name", "value": name}
        response = self.session.get(f"{self.base_path}/lookup", params=params)
        return UnitV4Lookup(**response.json())

    @validate_call
    def get_compatible(
        self, *, symbol: str | None = None, expression: str | None = None
    ) -> UnitV4Compatible:
        """Get the SI mapping and compatible unit families for a symbol or expression.

        Provide exactly one of ``symbol`` (a global unit symbol such as ``"g"``) or
        ``expression`` (a unit expression such as ``"1000*g"``). Use this to preview
        what Albert will resolve before creating a convertible unit.

        !!! example
            ```python
            compatible = client.units_v4.get_compatible(expression="1000*g")
            print(compatible.si_unit, compatible.ref_unit_value, compatible.dimension)
            # kg 1000 Mass
            print([f.name for f in compatible.unit_families])
            # ['Mass']
            ```

        Parameters
        ----------
        symbol : str, optional
            A global unit symbol to resolve.
        expression : str, optional
            A unit expression to resolve.

        Returns
        -------
        UnitV4Compatible
            The resolved reference unit, SI mapping, dimension and compatible families.
        """
        if (symbol is None) == (expression is None):
            raise ValueError("Exactly one of symbol or expression must be provided.")
        params = {"type": "symbol", "value": symbol} if symbol is not None else {}
        if expression is not None:
            params = {"type": "exp", "value": expression}
        response = self.session.get(f"{self.base_path}/compatible", params=params)
        return UnitV4Compatible(**response.json())
