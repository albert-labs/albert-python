from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import ReferenceAttributeId
from albert.resources.reference_attributes import ReferenceAttribute


class ReferenceAttributeCollection(BaseCollection):
    """
    ReferenceAttributeCollection is a collection class for managing reference attributes in Albert.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the ReferenceAttributeCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ReferenceAttributeCollection._api_version}/referenceattributes"

    def get_all(
        self,
        *,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[ReferenceAttribute]:
        """
        Get all reference attributes with pagination support.

        Parameters
        ----------
        start_key : str | None, optional
            The pagination key to start from.
        max_items : int | None, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[ReferenceAttribute]
            An iterator of reference attributes.
        """
        params = {"startKey": start_key}
        params = {k: v for k, v in params.items() if v is not None}

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [ReferenceAttribute(**item) for item in items],
        )

    def create(self, *, reference_attribute: ReferenceAttribute) -> ReferenceAttribute:
        """
        Create a reference attribute.

        Parameters
        ----------
        reference_attribute : ReferenceAttribute
            The reference attribute to create.

        Returns
        -------
        ReferenceAttribute
            The created reference attribute.
        """
        payload = reference_attribute.model_dump(
            by_alias=True,
            exclude_none=True,
            mode="json",
        )
        if reference_attribute.data_column is not None and payload.get("datacolumnId") is None:
            payload["datacolumnId"] = reference_attribute.data_column.id
        payload.pop("datacolumn", None)

        if reference_attribute.unit is not None and payload.get("unitId") is None:
            payload["unitId"] = reference_attribute.unit.id
        payload.pop("unit", None)

        if reference_attribute.parameters is not None:
            parameter_payloads = []
            for parameter in reference_attribute.parameters:
                serialized = parameter.model_dump(by_alias=True, exclude_none=True, mode="json")
                if parameter.unit is not None and serialized.get("unitId") is None:
                    serialized["unitId"] = parameter.unit.id
                serialized.pop("unit", None)
                parameter_payloads.append(serialized)
            payload["parameters"] = parameter_payloads

        response = self.session.post(self.base_path, json=payload)
        from rich import print

        print(payload)
        return ReferenceAttribute(**response.json())

    @validate_call
    def get_by_id(self, *, id: ReferenceAttributeId) -> ReferenceAttribute:
        """
        Get a reference attribute by its ID.

        Parameters
        ----------
        id : ReferenceAttributeId
            The reference attribute ID.

        Returns
        -------
        ReferenceAttribute
            The reference attribute.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return ReferenceAttribute(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[ReferenceAttributeId]) -> list[ReferenceAttribute]:
        """
        Get reference attributes by their IDs.

        Parameters
        ----------
        ids : list[ReferenceAttributeId]
            The reference attribute IDs.

        Returns
        -------
        list[ReferenceAttribute]
            The reference attributes.
        """
        if not ids:
            return []
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        items: list[ReferenceAttribute] = []
        for batch in batches:
            response = self.session.get(url, params={"id": batch})
            data = response.json()
            if isinstance(data, list):
                batch_items = data
            else:
                batch_items = data.get("items") or data.get("Items") or []
            items.extend(ReferenceAttribute(**item) for item in batch_items)
        return items

    @validate_call
    def delete(self, *, id: ReferenceAttributeId) -> None:
        """
        Delete a reference attribute by its ID.

        Parameters
        ----------
        id : ReferenceAttributeId
            The reference attribute ID.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
