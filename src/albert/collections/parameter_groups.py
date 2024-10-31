from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.parameter_groups import ParameterGroup, PGType
from albert.session import AlbertSession


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

    def _list_generator(
        self,
        *,
        text: str | None = None,
        offset: int | None = None,
        types: list[PGType] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 25,
    ) -> Generator[ParameterGroup, None, None]:
        params = {"limit": limit, "order": order_by.value}
        if text:
            params["text"] = text
        if offset:  # pragma: no cover
            params["offset"] = offset
        if types:
            params["types"] = types if isinstance(types, list) else [types]
        while True:
            response = self.session.get(self.base_path + "/search", params=params)
            pg_data = response.json().get("Items", [])
            if not pg_data or pg_data == []:
                break
            for pg in pg_data:
                yield self.get_by_id(id=pg["albertId"])
            offset = response.json().get("offset")
            if not offset:  # pragma: no cover
                break
            params["offset"] = int(offset) + int(limit)

    def list(
        self,
        *,
        text: str | None = None,
        types: list[PGType] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Iterator[ParameterGroup]:
        return self._list_generator(
            text=text,
            types=types,
            order_by=order_by,
        )

    def delete(self, *, id: str) -> None:
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def create(self, *, parameter_group: ParameterGroup) -> ParameterGroup:
        response = self.session.post(
            self.base_path, json=parameter_group.model_dump(by_alias=True, exclude_none=True)
        )
        return ParameterGroup(**response.json())

    def get_by_name(self, *, name: str) -> ParameterGroup | None:
        matches = self.list(text=name)
        for m in matches:
            if m.name.lower() == name.lower():
                return m
        return None

    def update(self, *, updated: ParameterGroup) -> ParameterGroup:
        existing = self.get_by_id(id=updated.id)
        path = f"{self.base_path}/{existing.id}"
        payload = self._generate_patch_payload(existing=existing, updated=updated)
        response = self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return ParameterGroup(**response.json())
