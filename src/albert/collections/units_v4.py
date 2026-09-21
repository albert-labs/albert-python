from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import UnitV4Id, ensure_unit_v4_id
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
    delete(id) -> None
        Delete a unit by its ID.
    lookup(symbol=..., name=...) -> UnitV4Lookup
        Check whether a unit symbol or name is already in use.
    get_compatible(symbol=..., expression=...) -> UnitV4Compatible
        Get the SI mapping and compatible unit families for a symbol or expression.
    merge(parent_id, child_ids, ...) -> str
        Merge units into a parent unit as a background job.
    """

    _api_version = "v4.0"
    _updatable_attributes = {"name", "description", "symbol", "synonyms", "unit_families"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a UnitV4Collection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnitV4Collection._api_version}/master-data/units"

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
            The unit to create. ``name`` and ``symbol`` must be unique within the tenant.

        Returns
        -------
        UnitV4
            The newly created unit, including its assigned ID and resolved SI fields.
        """
        payload = unit.model_dump(
            by_alias=True, mode="json", exclude_none=True, include=_CREATE_FIELDS
        )
        if "unitFamilies" in payload:
            payload["unitFamilies"] = [family["id"] for family in payload["unitFamilies"]]
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
            The unit ID: a UUID, or a legacy ``UNI...`` ID.

        Returns
        -------
        UnitV4
            The fully populated unit.
        """
        unit, _ = self._get_with_version(id=id)
        return unit

    def _get_with_version(self, *, id: str) -> tuple[UnitV4, str | None]:
        """Fetch a unit together with its current version, needed to update it."""
        response = self.session.get(f"{self.base_path}/{id}")
        return UnitV4(**response.json()), response.headers.get("ETag")

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
        is matched by its ``id``. Only fields you changed are sent; everything else is
        left untouched.

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
            The unit carrying the desired changes. Must have its ``id`` set.

        Returns
        -------
        UnitV4
            The updated unit.

        Raises
        ------
        ValueError
            If the unit has no ``id``, or if ``unit_families`` is changed on a
            convertible unit (families of convertible units are derived from the SI
            mapping and cannot be edited).

        Notes
        -----
        The following fields can be updated: ``name``, ``description``, ``symbol``,
        ``synonyms``. Non-convertible units can also update ``unit_families``. The SI
        mapping of a convertible unit (``si_unit``, ``si_value``, ``ref_unit``,
        ``ref_unit_exp``, ``ref_unit_value``) is fixed once created because changing
        it would alter historical measurements.
        """
        if unit.id is None:
            raise ValueError("The unit must have an id to be updated.")
        unit_id = ensure_unit_v4_id(unit.id)
        existing, version = self._get_with_version(id=unit_id)
        patch = self._generate_merge_patch(existing=existing, updated=unit)
        if not patch:
            return existing
        headers = dict(_MERGE_PATCH_HEADERS)
        if version is not None:
            headers["If-Match"] = version
        response = self.session.patch(f"{self.base_path}/{unit_id}", json=patch, headers=headers)
        return UnitV4(**response.json())

    @staticmethod
    def _generate_merge_patch(*, existing: UnitV4, updated: UnitV4) -> dict[str, Any]:
        """Build the set of changed, patchable fields between two units.

        Only attributes the caller explicitly set on ``updated`` participate; unset
        attributes leave the server value untouched.
        """
        patch: dict[str, Any] = {}
        for attr in ("name", "description", "symbol", "synonyms"):
            if attr not in updated.model_fields_set:
                continue
            new_value = getattr(updated, attr)
            if new_value != getattr(existing, attr):
                patch[attr] = new_value

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

    @validate_call
    def merge(
        self,
        *,
        parent_id: UnitV4Id,
        child_ids: list[UnitV4Id],
        webhook_url: str | None = None,
        webhook_method: str = "POST",
    ) -> str:
        """Merge units into a parent unit as a background job.

        Every reference to a child unit across the tenant is repointed to the parent
        unit. The merge runs asynchronously; this call returns as soon as the job is
        accepted.

        !!! example
            ```python
            job_id = client.units_v4.merge(parent_id="UNI1", child_ids=["UNI2", "UNI3"])
            ```

        Parameters
        ----------
        parent_id : UnitV4Id
            The unit that survives the merge.
        child_ids : list[UnitV4Id]
            The units to merge into ``parent_id``. At least one is required.
        webhook_url : str, optional
            A URL Albert calls when the job completes.
        webhook_method : str, optional
            HTTP method for the webhook call, ``"POST"`` (default) or ``"GET"``.

        Returns
        -------
        str
            The ID of the background merge job.
        """
        payload: dict[str, Any] = {"parentId": parent_id, "childIds": child_ids}
        if webhook_url is not None:
            payload["webhook"] = {"url": webhook_url, "method": webhook_method}
        response = self.session.post(f"{self.base_path}/merge", json=payload)
        return response.json()["id"]
