from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.parameter_groups import ParameterGroup, PGType
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ParameterGroupCollection(BaseCollection):
    _api_version = "v3"
    _updatable_attributes = {"name", "shortName"}
    # To do: Add the rest of the allowed attributes

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{ParameterGroupCollection._api_version}/parametergroups"

    def get_by_id(self, *, id: str) -> ParameterGroup:
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

    def list(
        self,
        *,
        limit: int = 25,
        offset: int | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        text: str | None = None,
        types: PGType | list[PGType] | None = None,
    ) -> Iterator[ParameterGroup]:
        def deserialize(items: list[dict]) -> list[ParameterGroup]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        params = {
            "limit": limit,
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
            deserialize=deserialize,
        )

    def delete(self, *, id: str) -> None:
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def create(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        response = self.session.post(
            self.base_path,
            json=parameter_group.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ParameterGroup(**response.json())

    def get_by_name(self, *, name: str) -> ParameterGroup | None:
        matches = self.list(text=name)
        for m in matches:
            if m.name.lower() == name.lower():
                return m
        return None

    def update(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        existing = self.get_by_id(id=parameter_group.id)
        path = f"{self.base_path}/{existing.id}"
        payload = self._generate_patch_payload(existing=existing, updated=parameter_group)
        response = self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return ParameterGroup(**response.json())
