from __future__ import annotations

from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.exceptions import AlbertHTTPError
from albert.resources.parameter_groups import (
    ParameterGroup,
    ParameterGroupSearchItem,
    PGType,
)
from albert.utils._patch import generate_parameter_group_patches


class ParameterGroupCollection(BaseCollection):
    """ParameterGroupCollection is a collection class for managing ParameterGroup entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "description", "metadata"}
    # To do: Add the rest of the allowed attributes

    def __init__(self, *, session: AlbertSession):
        """A collection for interacting with Albert parameter groups.

        Parameters
        ----------
        session : AlbertSession
            The Albert session to use for making requests.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterGroupCollection._api_version}/parametergroups"

    def get_by_id(self, *, id: str) -> ParameterGroup:
        """Get a parameter group by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter group to retrieve.

        Returns
        -------
        ParameterGroup
            The parameter group with the given ID.
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return ParameterGroup(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> ParameterGroup:
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
        order_by: OrderBy = OrderBy.DESCENDING,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[ParameterGroupSearchItem]:
        """
        Search for Parameter Groups matching the given criteria.

        Parameters
        ----------
        text : str, optional
            Text to search for.
        types : PGType or list of PGType, optional
            Filter by Parameter Group types.
        order_by : OrderBy, optional
            Order of results. Default is DESCENDING.
        offset : int, optional
            Offset to begin results from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        Iterator[ParameterGroupSearchItem]
            Iterator of ParameterGroupSearchItem entities, which are partial representations of Parameter Groups.
        """
        params = {
            "offset": offset,
            "order": order_by.value,
            "text": text,
            "types": [types] if isinstance(types, PGType) else types,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
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
        """
        Search and hydrate all Parameter Groups matching the given criteria.

        Parameters
        ----------
        text : str, optional
            Text to search for.
        types : PGType or list of PGType, optional
            Filter by Parameter Group types.
        order_by : OrderBy, optional
            Order of results. Default is DESCENDING.
        offset : int, optional
            Offset to begin results from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        Iterator[ParameterGroup]
            Iterator over Parameter Group entities.
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

    def delete(self, *, id: str) -> None:
        """Delete a parameter group by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter group to delete
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def create(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Create a new parameter group.

        Parameters
        ----------
        parameter_group : ParameterGroup
            The parameter group to create.

        Returns
        -------
        ParameterGroup
            The created parameter group.
        """

        response = self.session.post(
            self.base_path,
            json=parameter_group.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ParameterGroup(**response.json())

    def get_by_name(self, *, name: str) -> ParameterGroup | None:
        """Get a parameter group by its name.

        Parameters
        ----------
        name : str
            The name of the parameter group to retrieve.

        Returns
        -------
        ParameterGroup | None
            The parameter group with the given name, or None if not found.
        """
        matches = self.search(text=name)
        for m in matches:
            if m.name.lower() == name.lower():
                return m.hydrate()
        return None

    def update(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        """Update a parameter group.

        Parameters
        ----------
        parameter_group : ParameterGroup
            The updated ParameterGroup. The ParameterGroup must have an ID.

        Returns
        -------
        ParameterGroup
            The updated ParameterGroup as returned by the server.
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
        new_param_url = f"{self.base_path}/{parameter_group.id}/parameters"
        if len(new_parameter_values) > 0:
            self.session.put(
                url=new_param_url,
                json={
                    "Parameters": [
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in new_parameter_values
                    ],
                },
            )
        new_param_sequences = [x.sequence for x in new_parameter_values]
        # handle enum updates
        for sequence, ep in enum_patches.items():
            if sequence in new_param_sequences:
                # we don't need to handle enum updates for new parameters
                continue
            if len(ep) > 0:
                enum_url = f"{self.base_path}/{parameter_group.id}/parameters/{sequence}/enums"
                self.session.put(
                    url=enum_url,
                    json=ep,
                )
        if len(general_patches.data) > 0:
            # patch the general patches
            self.session.patch(
                url=path,
                json=general_patches.model_dump(mode="json", by_alias=True, exclude_none=True),
            )

        return self.get_by_id(id=parameter_group.id)
