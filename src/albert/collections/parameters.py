import json
import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.parameters import Parameter
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


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
            Returns the created parameter or the existing parameter if it already exists.
        """
        match = next(self.list(names=parameter.name, exact_match=True), None)
        if match is not None:
            logging.warning(
                f"Parameter with name {parameter.name} already exists. Returning existing parameter."
            )
            return match
        response = self.session.post(
            self.base_path,
            json=parameter.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Parameter(**response.json())

    def delete(self, *, id: str) -> None:
        """Delete a parameter by its ID.

        Parameters
        ----------
        id : str
            The ID of the parameter to delete.
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def list(
        self,
        *,
        ids: list[str] | None = None,
        names: str | list[str] = None,
        exact_match: bool = False,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | None = None,
        limit: int = 50,
        return_full: bool = True,
    ) -> Iterator[Parameter]:
        """Lists parameters that match the provided criteria.

        Parameters
        ----------
        ids : list[str] | None, optional
            A list of parameter IDs to retrieve, by default None
        names : str | list[str], optional
            A list of parameter names to retrieve, by default None
        exact_match : bool, optional
            Whether to match the name exactly, by default False
        order_by : OrderBy, optional
            The order in which to return results, by default OrderBy.DESCENDING
        return_full : bool, optional
            Whether to make additional API call to fetch the full object, by default True

        Yields
        ------
        Iterator[Parameter]
            An iterator of Parameters matching the given criteria.
        """

        def deserialize(items: list[dict]) -> Iterator[Parameter]:
            if return_full:
                for item in items:
                    id = item["albertId"]
                    try:
                        yield self.get_by_id(id=id)
                    except AlbertHTTPError as e:
                        logger.warning(f"Error fetching Parameter '{id}': {e}")
            else:
                yield from (Parameter(**item) for item in items)

        params = {"limit": limit, "orderBy": order_by, "parameters": ids, "startKey": start_key}
        if names:
            params["name"] = [names] if isinstance(names, str) else names
            params["exactMatch"] = json.dumps(exact_match)

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
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
