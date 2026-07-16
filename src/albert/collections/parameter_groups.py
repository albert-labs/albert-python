from __future__ import annotations

from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ParameterGroupId
from albert.core.utils import ensure_list
from albert.exceptions import AlbertHTTPError
from albert.resources.parameter_groups import (
    ParameterGroup,
    ParameterGroupSearchItem,
    PGType,
)
from albert.utils._patch import (
    create_parameters_with_enums,
    generate_parameter_group_patches,
)

DEFAULT_ADDITIONAL_FIELDS = [
    "acl",
    "createdAt",
    "createdByName",
    "metadata",
    "owner",
    "tags",
    "team",
]


class ParameterGroupCollection(BaseCollection):
    """Manage Parameter Groups in the Albert platform.

    A Parameter Group (PRG, IDs formatted ``PRG...``) is a reusable set of
    [`Parameter`][albert.resources.parameters.Parameter] entities together with their
    values, units, and validation rules. Whereas a Data Template's parameters
    always relate to a given measurement, a Parameter Group is about *making* the
    sample and/or *prepping* it for measurement (e.g. a mixing step, a cure
    schedule). Some Parameter Groups drive Batch Tasks
    ([`BatchTask`][albert.resources.tasks.BatchTask]); others are stacked within a task.

    The group's [`PGType`][albert.resources.parameter_groups.PGType] records which kind of task the group relates to.
    A Parameter Group's parameters, together with a Data Template's parameters,
    are fixed to setpoints inside a [`Workflow`][albert.resources.workflows.Workflow].
    Test standards (e.g. ASTM or ISO) are stored under the ``"Standards"`` key of
    a group's ``metadata``.

    This collection is accessed as ``client.parameter_groups``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for parameter group requests.

    Methods
    -------
    create(parameter_group) -> ParameterGroup
        Create a new parameter group.
    get_by_id(id) -> ParameterGroup
        Get a single fully populated group by its ID.
    get_by_ids(ids) -> list[ParameterGroup]
        Get many groups by their IDs in batches.
    get_by_name(name) -> ParameterGroup | None
        Get a single group by exact (case-insensitive) name.
    search(...) -> Iterator[ParameterGroupSearchItem]
        Fast, lightweight search returning partial groups (best for lookups/counts).
    get_all(...) -> Iterator[ParameterGroup]
        Same filters as search, but returns fully populated groups (slower).
    update(parameter_group) -> ParameterGroup
        Update an existing group.
    delete(id) -> None
        Delete a group by its ID.

    Examples
    --------
    ```python
    from albert import Albert

    client = Albert()
    pg = client.parameter_groups.get_by_id(id="PRG1")
    print(pg.name, pg.type)
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "description", "metadata"}
    # To do: Add the rest of the allowed attributes

    def __init__(self, *, session: AlbertSession):
        """Initialize a ParameterGroupCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterGroupCollection._api_version}/parametergroups"

    @validate_call
    def get_by_id(self, *, id: ParameterGroupId) -> ParameterGroup:
        """Get a single, fully populated parameter group by its ID.

        For retrieving many groups at once, use [`get_by_ids`][albert.collections.parameter_groups.ParameterGroupCollection.get_by_ids]. To find groups
        without knowing their IDs, use [`search`][albert.collections.parameter_groups.ParameterGroupCollection.search], [`get_all`][albert.collections.parameter_groups.ParameterGroupCollection.get_all], or
        [`get_by_name`][albert.collections.parameter_groups.ParameterGroupCollection.get_by_name].

        Parameters
        ----------
        id : ParameterGroupId
            The Parameter Group ID (format ``PRG...``, e.g. ``"PRG1"``).

        Returns
        -------
        ParameterGroup
            The fully populated parameter group.

        Examples
        --------
        ```python
        pg = client.parameter_groups.get_by_id(id="PRG1")
        pg.name
        # 'Mixing Step'
        ```
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return ParameterGroup(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[ParameterGroupId]) -> list[ParameterGroup]:
        """Get multiple fully populated parameter groups by their IDs.

        Requests are automatically split into batches, so arbitrarily long ID
        lists are supported. Groups not found are omitted from the result.

        Parameters
        ----------
        ids : list[ParameterGroupId]
            The Parameter Group IDs to retrieve (format ``PRG...``).

        Returns
        -------
        list[ParameterGroup]
            The matching parameter groups. Order is not guaranteed to match the
            input.

        Examples
        --------
        ```python
        groups = client.parameter_groups.get_by_ids(ids=["PRG1", "PRG2"])
        [g.name for g in groups]
        # ['Mixing Step', 'Cure Schedule']
        ```
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            ParameterGroup(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def search(
        self,
        *,
        text: str | None = None,
        types: PGType | list[PGType] | None = None,
        owner: str | list[str] | None = None,
        tags: str | list[str] | None = None,
        parameters: str | list[str] | None = None,
        additional_field: str | list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[ParameterGroupSearchItem]:
        """Search for parameter groups matching the given filters.

        Returns lightweight, partially populated results and is the fastest way to
        look groups up (best for name lookups, counts, or feeding IDs into another
        call). When you need complete groups, use [`get_all`][albert.collections.parameter_groups.ParameterGroupCollection.get_all] with the same
        filters, or pass the resulting IDs to [`get_by_ids`][albert.collections.parameter_groups.ParameterGroupCollection.get_by_ids]. Results are
        returned as a lazily paginated iterator, so iterating fetches additional
        pages on demand.

        Parameters
        ----------
        text : str, optional
            Free-text query matched against group name and related fields.
        types : PGType or list[PGType], optional
            Filter by parameter group type (``general``, ``batch``, or
            ``property``).
        owner : str or list[str], optional
            Filter by owner name(s).
        tags : str or list[str], optional
            Filter by tag name(s).
        parameters : str or list[str], optional
            Filter by parameter name(s).
        additional_field : str or list[str], optional
            Additional fields to include on each returned search item. If omitted,
            a default set (ACL, creation info, metadata, owner, tags, and team) is
            requested.
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Yields
        ------
        ParameterGroupSearchItem
            Partially populated search results. Call ``.hydrate()`` on an item to
            fetch its full [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup].

        Examples
        --------
        ```python
        from albert.resources.parameter_groups import PGType

        hits = client.parameter_groups.search(
            text="mixing",
            types=PGType.BATCH,
            max_items=10,
        )
        first = next(iter(hits))
        first.name
        # 'Mixing Step'
        ```
        """
        payload = {
            "offset": offset,
            "order": order_by,
            "text": text,
            "types": ensure_list(types),
            "owner": ensure_list(owner),
            "tags": ensure_list(tags),
            "parameters": ensure_list(parameters),
            "additionalField": (
                ensure_list(additional_field)
                if additional_field is not None
                else list(DEFAULT_ADDITIONAL_FIELDS)
            ),
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            method="POST",
            json=payload,
            max_items=max_items,
            deserialize=lambda items: [
                ParameterGroupSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
        types: PGType | list[PGType] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[ParameterGroup]:
        """Get fully populated parameter groups matching the given filters.

        Accepts the same filters as [`search`][albert.collections.parameter_groups.ParameterGroupCollection.search] but returns complete
        [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup] entities rather than lightweight search results.
        This is slower because it fetches full detail for every match, so prefer
        [`search`][albert.collections.parameter_groups.ParameterGroupCollection.search] when you only need names, IDs, or counts. Results are
        returned as a lazily paginated iterator.

        Parameters
        ----------
        text : str, optional
            Free-text query matched against group name and related fields.
        types : PGType or list[PGType], optional
            Filter by parameter group type (``general``, ``batch``, or
            ``property``).
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Yields
        ------
        ParameterGroup
            Fully populated parameter groups.

        Examples
        --------
        ```python
        for pg in client.parameter_groups.get_all(text="mixing", max_items=25):
            print(pg.id, pg.name)
        ```
        """
        for item in self.search(
            text=text,
            types=types,
            order_by=order_by,
            offset=offset,
            max_items=max_items,
        ):
            try:
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:  # pragma: no cover
                logger.warning(f"Error fetching parameter group {item.id}: {e}")

    @validate_call
    def delete(self, *, id: ParameterGroupId) -> None:
        """Delete a parameter group by its ID.

        This permanently removes the parameter group.

        Parameters
        ----------
        id : ParameterGroupId
            The Parameter Group ID to delete (format ``PRG...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.parameter_groups.delete(id="PRG1")
        ```
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def create(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Create a new parameter group.

        Build a [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup] with a ``name``, a [`PGType`][albert.resources.parameter_groups.PGType], and a
        list of [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] entries, then pass it here. Each
        [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] must reference an existing
        [`Parameter`][albert.resources.parameters.Parameter] (by ``id`` or ``parameter``).

        Parameters
        ----------
        parameter_group : ParameterGroup
            The parameter group to create.

        Returns
        -------
        ParameterGroup
            The newly created group, populated with its assigned Parameter Group ID.

        Examples
        --------
        ```python
        from albert.resources.parameter_groups import (
            ParameterGroup,
            ParameterValue,
            PGType,
        )

        pg = ParameterGroup(
            name="Mixing Step",
            type=PGType.BATCH,
            parameters=[ParameterValue(id="PRM1", value="500")],
        )
        created = client.parameter_groups.create(parameter_group=pg)
        created.id
        # 'PRG1'
        ```
        """

        response = self.session.post(
            self.base_path,
            json=parameter_group.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ParameterGroup(**response.json())

    def get_by_name(self, *, name: str) -> ParameterGroup | None:
        """Get a single, fully populated parameter group by its exact name.

        Searches for the name and returns the first group whose name matches
        exactly (case-insensitive). Returns None when no exact match is found.

        Parameters
        ----------
        name : str
            The name of the parameter group to retrieve.

        Returns
        -------
        ParameterGroup or None
            The matching parameter group, or None if no exact match is found.

        Examples
        --------
        ```python
        pg = client.parameter_groups.get_by_name(name="Mixing Step")
        pg.id if pg else "no match"
        # 'PRG1'
        ```
        """
        matches = self.search(text=name)
        for m in matches:
            if m.name.lower() == name.lower():
                return m.hydrate()
        return None

    def update(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Update an existing parameter group.

        Fetch the group (e.g. with [`get_by_id`][albert.collections.parameter_groups.ParameterGroupCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Adding new
        [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] entries to ``parameters`` also creates those
        parameters on the group. Only the fields listed in Notes are applied;
        changes to other fields are ignored.

        Parameters
        ----------
        parameter_group : ParameterGroup
            The group to update. Must have a valid ``id``.

        Returns
        -------
        ParameterGroup
            The updated parameter group.

        Notes
        -----
        The following fields can be updated: ``description``, ``metadata``,
        ``name``, and, per parameter, ``value``, ``unit``, ``required``, and
        ``validation``.

        Examples
        --------
        ```python
        pg = client.parameter_groups.get_by_id(id="PRG1")
        pg.description = "Updated description"
        updated = client.parameter_groups.update(parameter_group=pg)
        updated.description
        # 'Updated description'
        ```
        """
        existing = self.get_by_id(id=parameter_group.id)
        path = f"{self.base_path}/{existing.id}"

        base_payload = self._generate_patch_payload(
            existing=existing, updated=parameter_group, generate_metadata_diff=True
        )

        general_patches, new_parameter_values, enum_patches = generate_parameter_group_patches(
            initial_patches=base_payload,
            updated_parameter_group=parameter_group,
            existing_parameter_group=existing,
        )

        # add new parameters
        if len(new_parameter_values) > 0:
            create_parameters_with_enums(
                session=self.session,
                parameters_base_url=f"{self.base_path}/{parameter_group.id}/parameters",
                patch_url=f"{self.base_path}/{parameter_group.id}",
                parameters=new_parameter_values,
            )

        # new_parameter_values have sequence=None before being sent, so this
        # guard never matches in practice, enum updates on new params are
        # handled above by create_parameters_with_enums.
        new_param_sequences = [x.sequence for x in new_parameter_values]
        # handle enum updates for existing parameters
        for sequence, ep in enum_patches.items():
            if sequence in new_param_sequences:
                continue
            if len(ep) > 0:
                self.session.put(
                    url=f"{self.base_path}/{parameter_group.id}/parameters/{sequence}/enums",
                    json=ep,
                )
        if len(general_patches.data) > 0:
            # patch the general patches
            self.session.patch(
                url=path,
                json=general_patches.model_dump(mode="json", by_alias=True, exclude_none=True),
            )

        return self.get_by_id(id=parameter_group.id)
