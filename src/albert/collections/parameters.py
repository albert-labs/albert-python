import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.resources.parameters import Parameter


class ParameterCollection(BaseCollection):
    """ParameterCollection is a collection class for managing Parameter entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initializes the ParameterCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterCollection._api_version}/parameters"

    def get_by_id(self, *, id: str) -> Parameter:
        """Retrieve a parameter by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter to retrieve.

        Returns
        -------
        Parameter
            The parameter with the given ID.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Parameter(**response.json())

    def create(self, *, parameter: Parameter) -> Parameter:
        """Create a new parameter.

        Parameters
        ----------
        parameter : Parameter
            The parameter to create.

        Returns
        -------
        Parameter
            Returns the created parameter.
        """
        response = self.session.post(
            self.base_path,
            json=parameter.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Parameter(**response.json())

    def get_or_create(self, *, parameter: Parameter) -> Parameter:
        """Retrieves a Parameter or creates it if it does not exist.

        Parameters
        ----------
        parameter : Parameter
            The parameter to get or create.

        Returns
        -------
        Parameter
            The existing or newly created parameter.
        """
        match = next(self.get_all(names=parameter.name, exact_match=True, max_items=1), None)
        if match:
            logging.warning(
                f"Parameter with name {parameter.name} already exists. Returning existing parameter."
            )
            return match
        return self.create(parameter=parameter)

    def delete(self, *, id: str) -> None:
        """Delete a parameter by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter to delete.
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def get_all(
        self,
        *,
        ids: list[str] | None = None,
        names: str | list[str] = None,
        exact_match: bool = False,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Parameter]:
        """
        Retrieve all Parameter items with optional filters.

        Parameters
        ----------
        ids : list[str], optional
            A list of parameter IDs to retrieve.
        names : str or list[str], optional
            One or more parameter names to filter by.
        exact_match : bool, optional
            Whether to require exact name matches. Default is False.
        order_by : OrderBy, optional
            Sort order of results. Default is DESCENDING.
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Parameter]
            An iterator of Parameters matching the given criteria.
        """

        def deserialize(items: list[dict]) -> Iterator[Parameter]:
            yield from (Parameter(**item) for item in items)

        params = {
            "orderBy": order_by.value,
            "parameters": ids,
            "startKey": start_key,
        }
        if names:
            params["name"] = [names] if isinstance(names, str) else names
            params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=deserialize,
        )

    def _is_metadata_item_list(
        self, *, existing_object: Parameter, updated_object: Parameter, metadata_field: str
    ):
        if not metadata_field.startswith("Metadata."):
            return False
        else:
            metadata_field = metadata_field.split(".")[1]
        if existing_object.metadata is None:
            existing_object.metadata = {}
        if updated_object.metadata is None:
            updated_object.metadata = {}
        existing = existing_object.metadata.get(metadata_field, None)
        updated = updated_object.metadata.get(metadata_field, None)
        return isinstance(existing, list) or isinstance(updated, list)

    def update(self, *, parameter: Parameter) -> Parameter:
        """Update a parameter.

        Parameters
        ----------
        parameter : Parameter
            The updated parameter to save. The parameter must have an ID.

        Returns
        -------
        Parameter
            The updated parameter as returned by the server.
        """
        existing = self.get_by_id(id=parameter.id)
        payload = self._generate_patch_payload(
            existing=existing,
            updated=parameter,
        )
        payload_dump = payload.model_dump(mode="json", by_alias=True)
        for i, change in enumerate(payload_dump["data"]):
            if not self._is_metadata_item_list(
                existing_object=existing,
                updated_object=parameter,
                metadata_field=change["attribute"],
            ):
                change["operation"] = "update"
                if "newValue" in change and change["newValue"] is None:
                    del change["newValue"]
                if "oldValue" in change and change["oldValue"] is None:
                    del change["oldValue"]
                payload_dump["data"][i] = change
        if len(payload_dump["data"]) == 0:
            return parameter
        for e in payload_dump["data"]:
            self.session.patch(
                f"{self.base_path}/{parameter.id}",
                json={"data": [e]},
            )
        return self.get_by_id(id=parameter.id)
