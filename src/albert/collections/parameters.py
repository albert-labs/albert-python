import logging
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ParameterId
from albert.core.utils import ensure_list
from albert.resources.parameters import Parameter


class ParameterCollection(BaseCollection):
    """Manage Parameters in the Albert platform.

    A Parameter (ID format ``PRM...``, e.g. ``"PRM1"``) is the definition of a
    single condition or input variable used when running experiments, such as
    Temperature, Spin Speed, or Instrument. It is often called an "indirect
    variable": the Parameter itself only names the variable, and its actual value
    and unit are fixed to a setpoint later, inside a [`Workflow`][albert.resources.workflows.Workflow].

    Parameters are the building blocks of Parameter Groups
    ([`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup]) and form the
    parameter side of Data Templates
    ([`DataTemplate`][albert.resources.data_templates.DataTemplate]).

    This collection is accessed as ``client.parameters``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for parameter requests.

    Methods
    -------
    create(parameter) -> Parameter
        Create a new parameter.
    get_or_create(parameter) -> Parameter
        Return the existing parameter matching by name, or create it.
    get_by_id(id) -> Parameter
        Retrieve a single parameter by its Parameter ID.
    get_all(...) -> Iterator[Parameter]
        Search for parameters by ID or name.
    update(parameter) -> Parameter
        Apply changes to an existing parameter.
    delete(id) -> None
        Delete a parameter by its Parameter ID.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        param = client.parameters.get_by_id(id="PRM1")
        param.name
        # 'Temperature'
        ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a ParameterCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterCollection._api_version}/parameters"

    @validate_call
    def get_by_id(self, *, id: ParameterId) -> Parameter:
        """Retrieve a single parameter by its ID.

        To find parameters without knowing their IDs, use [`get_all`][albert.collections.parameters.ParameterCollection.get_all].

        Parameters
        ----------
        id : ParameterId
            The Parameter ID (format ``PRM...``, e.g. ``"PRM1"``).

        Returns
        -------
        Parameter
            The parameter with the given ID.

        !!! example
            ```python
            param = client.parameters.get_by_id(id="PRM1")
            param.name
            # 'Temperature'
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Parameter(**response.json())

    def create(self, *, parameter: Parameter) -> Parameter:
        """Create a new parameter.

        This registers a new condition or input variable (e.g. Temperature or Spin
        Speed) that can then be used in Parameter Groups and Data Templates. To
        avoid creating duplicates when a parameter of the same name may already
        exist, use [`get_or_create`][albert.collections.parameters.ParameterCollection.get_or_create] instead.

        Parameters
        ----------
        parameter : Parameter
            The parameter to create. Only ``name`` is required.

        Returns
        -------
        Parameter
            The newly created parameter, populated with its assigned Parameter ID.

        !!! example
            ```python
            from albert.resources.parameters import Parameter
            param = client.parameters.create(parameter=Parameter(name="Spin Speed"))
            param.id
            # 'PRM1'
            ```
        """
        response = self.session.post(
            self.base_path,
            json=parameter.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Parameter(**response.json())

    def get_or_create(self, *, parameter: Parameter) -> Parameter:
        """Return the existing parameter matching by name, or create it.

        Matches an existing parameter by exact ``name``. If a match is found, it is
        returned unchanged; otherwise a new parameter is created via [`create`][albert.collections.parameters.ParameterCollection.create].
        Use this to avoid creating duplicate parameters.

        Parameters
        ----------
        parameter : Parameter
            The parameter to get or create. Matched on ``name``.

        Returns
        -------
        Parameter
            The existing or newly created parameter.

        !!! example
            ```python
            from albert.resources.parameters import Parameter
            param = client.parameters.get_or_create(parameter=Parameter(name="Temperature"))
            param.id
            # 'PRM1'
            ```
        """
        for match in self.get_all(names=parameter.name, exact_match=False):
            if match.name == parameter.name:
                logging.warning(
                    f"Parameter with name {parameter.name} already exists. Returning existing parameter."
                )
                return match
        return self.create(parameter=parameter)

    @validate_call
    def delete(self, *, id: ParameterId) -> None:
        """Delete a parameter by its ID.

        This permanently removes the parameter.

        Parameters
        ----------
        id : ParameterId
            The Parameter ID to delete (format ``PRM...``).

        Returns
        -------
        None

        !!! example
            ```python
            client.parameters.delete(id="PRM1")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_all(
        self,
        *,
        ids: list[ParameterId] | None = None,
        names: str | list[str] = None,
        exact_match: bool = False,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Parameter]:
        """Search for parameters, optionally filtered by ID or name.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand. With no filters, iterates over all parameters.

        Parameters
        ----------
        ids : list[ParameterId], optional
            Restrict results to these Parameter IDs (format ``PRM...``).
        names : str or list[str], optional
            One or more parameter names to filter by.
        exact_match : bool, optional
            When True, only parameters whose name matches ``names`` exactly are
            returned. When False (default), name matching is partial.
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        start_key : str, optional
            Pagination key to resume from. Usually left unset.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[Parameter]
            A lazily paginated iterator of parameters matching the given criteria.

        !!! example
            ```python
            for param in client.parameters.get_all(names="Temperature", max_items=10):
                print(param.id, param.name)
            ```
        """

        def deserialize(items: list[dict]) -> Iterator[Parameter]:
            yield from (Parameter(**item) for item in items)

        params = {
            "orderBy": order_by,
            "parameters": ids,
            "startKey": start_key,
        }
        params["name"] = ensure_list(names)
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
        """Update an existing parameter.

        Fetch the parameter (e.g. with [`get_by_id`][albert.collections.parameters.ParameterCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. Only the fields listed in
        Notes are applied; changes to other fields are ignored.

        Parameters
        ----------
        parameter : Parameter
            The parameter to update. Must have a valid ``id``.

        Returns
        -------
        Parameter
            The updated parameter as returned by the server.

        Notes
        -----
        The following fields can be updated: ``metadata``, ``name``.

        !!! example
            ```python
            param = client.parameters.get_by_id(id="PRM1")
            param.name = "Bath Temperature"
            updated = client.parameters.update(parameter=param)
            updated.name
            # 'Bath Temperature'
            ```
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
