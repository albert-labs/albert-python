import json
import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.parameters import Parameter
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ParameterCollection(BaseCollection):
    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterCollection._api_version}/parameters"

    def get_by_id(self, *, id: str) -> Parameter:
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Parameter(**response.json())

    def create(self, *, parameter: Parameter) -> Parameter:
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
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def list(
        self,
        *,
        limit: int = 50,
        ids: list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        names: str | list[str] = None,
        exact_match: bool = False,
        start_key: str | None = None,
    ) -> Iterator[Parameter]:
        params = {"limit": limit, "orderBy": order_by, "parameters": ids, "startKey": start_key}
        if names:
            params["name"] = [names] if isinstance(names, str) else names
            params["exactMatch"] = json.dumps(exact_match)

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [Parameter(**item) for item in items],
        )

    def update(self, *, parameter: Parameter) -> Parameter:
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=parameter.id),
            updated=parameter,
        )
        self.session.patch(
            f"{self.base_path}/{parameter.id}",
            json=payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=parameter.id)
