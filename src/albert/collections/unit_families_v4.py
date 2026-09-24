from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import UnitFamilyV4Id, ensure_unit_family_v4_id
from albert.resources.unit_families_v4 import (
    UnitFamilyV4,
    UnitFamilyV4Lookup,
    UnitFamilyV4Origin,
    UnitFamilyV4SearchItem,
    UnitFamilyV4Type,
)

_SEARCH_PAGE_SIZE = 100  # page size used for the v4 unit family search endpoint
_CREATE_FIELDS = {"name", "description", "type", "ref_unit", "unit_expression"}
_MERGE_PATCH_HEADERS = {"Content-Type": "application/merge-patch+json"}


class UnitFamilyV4Collection(BaseCollection):
    """Manage Unit Families in the Albert platform (🧪 Beta).

    A unit family groups related units (for example ``Mass`` holds ``kg``, ``g`` and
    ``lb``). Convertible families have an SI basis that Albert resolves on create.
    See [`UnitFamilyV4`][albert.resources.unit_families_v4.UnitFamilyV4].

    This collection is accessed as ``client.unit_families_v4``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert
        from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type

        client = Albert()
        family = client.unit_families_v4.create(
            unit_family=UnitFamilyV4(name="Force", type=UnitFamilyV4Type.CONVERTIBLE, unit_expression="kg*m/s^2")
        )
        print(family.id, family.si_unit, family.dimension)
        # UNF7 N Force
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for unit family requests.

    Methods
    -------
    create(unit_family) -> UnitFamilyV4
        Create a new unit family.
    get_by_id(id) -> UnitFamilyV4
        Get a single unit family by its ID.
    get_by_ids(ids) -> list[UnitFamilyV4SearchItem]
        Get many unit families by their IDs.
    search(...) -> Iterator[UnitFamilyV4SearchItem]
        Search for unit families matching the given filters.
    update(unit_family) -> UnitFamilyV4
        Update an existing unit family.
    delete(id) -> None
        Delete a unit family by its ID.
    lookup(name) -> UnitFamilyV4Lookup
        Check whether a unit family name is already in use.
    """

    _api_version = "v4.0"
    _updatable_attributes = {"name", "description"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a UnitFamilyV4Collection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnitFamilyV4Collection._api_version}/master-data/unit-families"

    @validate_call
    def create(self, *, unit_family: UnitFamilyV4) -> UnitFamilyV4:
        """Create a new unit family.

        For a convertible family, provide ``ref_unit`` (a global unit symbol) or
        ``unit_expression``; Albert resolves the SI unit and dimension. A
        non-convertible family needs only a name and type.

        !!! example
            ```python
            from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type

            mass = client.unit_families_v4.create(
                unit_family=UnitFamilyV4(name="Mass", type=UnitFamilyV4Type.CONVERTIBLE, ref_unit="kg")
            )
            count = client.unit_families_v4.create(
                unit_family=UnitFamilyV4(name="Count", type=UnitFamilyV4Type.NON_CONVERTIBLE)
            )
            ```

        Parameters
        ----------
        unit_family : UnitFamilyV4
            The unit family to create. ``name`` must be unique within the tenant.

        Returns
        -------
        UnitFamilyV4
            The newly created unit family, including its assigned ID and resolved SI fields.
        """
        payload = unit_family.model_dump(
            by_alias=True, mode="json", exclude_none=True, include=_CREATE_FIELDS
        )
        response = self.session.post(self.base_path, json=payload)
        return UnitFamilyV4(**response.json())

    @validate_call
    def get_by_id(self, *, id: UnitFamilyV4Id) -> UnitFamilyV4:
        """Get a single unit family by its ID.

        !!! example
            ```python
            family = client.unit_families_v4.get_by_id(id="UNF1")
            print(family.name, family.units)
            # Mass ['kg', 'g', 'mg', 'lb', 'oz']
            ```

        Parameters
        ----------
        id : UnitFamilyV4Id
            The unit family ID: a UUID, or a legacy ``UNF...`` ID.

        Returns
        -------
        UnitFamilyV4
            The fully populated unit family, including linked unit symbols.
        """
        unit_family, _ = self._get_with_version(id=id)
        return unit_family

    def _get_with_version(self, *, id: str) -> tuple[UnitFamilyV4, str | None]:
        """Fetch a unit family together with its current version, needed to update it."""
        response = self.session.get(f"{self.base_path}/{id}")
        return UnitFamilyV4(**response.json()), response.headers.get("ETag")

    @validate_call
    def get_by_ids(self, *, ids: list[UnitFamilyV4Id]) -> list[UnitFamilyV4SearchItem]:
        """Get many unit families by their IDs.

        IDs are fetched in batches, so arbitrarily long lists are supported. The
        returned records omit the computed ``units`` and ``same_si_basis_families``
        fields; use
        [`get_by_id`][albert.collections.unit_families_v4.UnitFamilyV4Collection.get_by_id]
        when you need them.

        !!! example
            ```python
            families = client.unit_families_v4.get_by_ids(ids=["UNF1", "UNF2"])
            ```

        Parameters
        ----------
        ids : list[UnitFamilyV4Id]
            The unit family IDs to retrieve.

        Returns
        -------
        list[UnitFamilyV4SearchItem]
            The matching unit families. Families not found are omitted.
        """
        families: list[UnitFamilyV4SearchItem] = []
        for start in range(0, len(ids), _SEARCH_PAGE_SIZE):
            batch = ids[start : start + _SEARCH_PAGE_SIZE]
            response = self.session.post(
                f"{self.base_path}/search", json={"id": batch, "limit": _SEARCH_PAGE_SIZE}
            )
            data = response.json()
            families.extend(
                UnitFamilyV4SearchItem(**item)
                for item in data.get("items") or data.get("Items") or []
            )
        return families

    def search(
        self,
        *,
        text: str | None = None,
        status: Status | None = None,
        origin: list[UnitFamilyV4Origin] | None = None,
        type: list[UnitFamilyV4Type] | None = None,
        dimension: list[str] | None = None,
        created_by: list[str] | None = None,
        sort_by: str | None = None,
        order_by: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[UnitFamilyV4SearchItem]:
        """Search for unit families matching the given filters.

        Results are fetched page by page as you iterate. Call with no filters to
        list every unit family visible to the tenant, including Albert-managed
        families.

        !!! example
            ```python
            from albert.resources.unit_families_v4 import UnitFamilyV4Type

            for family in client.unit_families_v4.search(
                type=[UnitFamilyV4Type.CONVERTIBLE], dimension=["Mass"], max_items=20
            ):
                print(family.name, family.si_unit)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text search across unit family names.
        status : Status, optional
            Restrict results to active or inactive families.
        origin : list[UnitFamilyV4Origin], optional
            Restrict results to the given origins (Albert-managed or custom).
        type : list[UnitFamilyV4Type], optional
            Restrict results to convertible and/or non-convertible families.
        dimension : list[str], optional
            Restrict results to the given physical dimensions (for example ``"Mass"``).
        created_by : list[str], optional
            Restrict results to families created by the given user IDs.
        sort_by : str, optional
            The field to sort by (for example ``"name"``).
        order_by : OrderBy, optional
            Sort direction. Defaults to the backend ordering.
        max_items : int, optional
            Maximum number of families to yield. Defaults to ``None`` (all results).

        Returns
        -------
        Iterator[UnitFamilyV4SearchItem]
            A lazily paginated iterator of matching unit families.
        """
        payload = {
            "text": text,
            "status": status,
            "origin": origin,
            "type": type,
            "dimension": dimension,
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
            deserialize=lambda items: [UnitFamilyV4SearchItem(**item) for item in items],
        )

    @validate_call
    def update(self, *, unit_family: UnitFamilyV4) -> UnitFamilyV4:
        """Update an existing unit family.

        Fetch a family (e.g. via
        [`get_by_id`][albert.collections.unit_families_v4.UnitFamilyV4Collection.get_by_id]),
        modify the updatable fields on the returned object, then pass it here. The
        family is matched by its ``id``. Only fields you changed are sent.

        !!! example
            ```python
            family = client.unit_families_v4.get_by_id(id="UNF1")
            family.description = "Units of mass, including imperial units"
            updated = client.unit_families_v4.update(unit_family=family)
            ```

        Parameters
        ----------
        unit_family : UnitFamilyV4
            The unit family carrying the desired changes. Must have its ``id`` set.

        Returns
        -------
        UnitFamilyV4
            The updated unit family.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``. The type and
        SI basis of a family are fixed once created.
        """
        if unit_family.id is None:
            raise ValueError("The unit family must have an id to be updated.")
        family_id = ensure_unit_family_v4_id(unit_family.id)
        existing, version = self._get_with_version(id=family_id)
        patch = self._generate_merge_patch(existing=existing, updated=unit_family)
        if not patch:
            return existing
        headers = dict(_MERGE_PATCH_HEADERS)
        if version is not None:
            headers["If-Match"] = version
        response = self.session.patch(f"{self.base_path}/{family_id}", json=patch, headers=headers)
        return UnitFamilyV4(**response.json())

    @staticmethod
    def _generate_merge_patch(*, existing: UnitFamilyV4, updated: UnitFamilyV4) -> dict[str, Any]:
        """Build the set of changed, patchable fields between two unit families.

        Only attributes the caller explicitly set on ``updated`` participate; unset
        attributes leave the server value untouched.
        """
        patch: dict[str, Any] = {}
        for attr in ("name", "description"):
            if attr not in updated.model_fields_set:
                continue
            new_value = getattr(updated, attr)
            if new_value != getattr(existing, attr):
                patch[attr] = new_value
        return patch

    @validate_call
    def delete(self, *, id: UnitFamilyV4Id) -> None:
        """Delete a unit family by its ID.

        The family is deactivated rather than removed, and its name becomes available
        for reuse.

        !!! example
            ```python
            client.unit_families_v4.delete(id="UNF1")
            ```

        Parameters
        ----------
        id : UnitFamilyV4Id
            The unit family ID to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def lookup(self, *, name: str) -> UnitFamilyV4Lookup:
        """Check whether a unit family name is already in use.

        Also returns families whose name matches ignoring case, so you can warn
        before creating a confusingly similar family.

        !!! example
            ```python
            result = client.unit_families_v4.lookup(name="Mass")
            if result.exists:
                print("Mass already exists")
            ```

        Parameters
        ----------
        name : str
            The unit family name to check (exact, case-sensitive match).

        Returns
        -------
        UnitFamilyV4Lookup
            Whether an exact match exists, plus any similarly named families.
        """
        response = self.session.get(
            f"{self.base_path}/lookup", params={"attr": "name", "value": name}
        )
        return UnitFamilyV4Lookup(**response.json())
