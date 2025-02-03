from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.data_templates import DataTemplate
from albert.resources.identifiers import DataTemplateId
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class DataTemplateCollection(BaseCollection):
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DataTemplateCollection._api_version}/datatemplates"

    def create(self, *, data_template: DataTemplate) -> DataTemplate:
        response = self.session.post(
            self.base_path,
            json=data_template.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return DataTemplate(**response.json())

    def get_by_id(self, *, id: DataTemplateId) -> DataTemplate:
        response = self.session.get(f"{self.base_path}/{id}")
        return DataTemplate(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> list[DataTemplate]:
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        return [
            DataTemplate(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_by_name(self, *, name: str) -> DataTemplate | None:
        hits = list(self.list(name=name))
        for h in hits:
            if h.name.lower() == name.lower():
                return h
        return None

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | None = None,
        user_id: str | None = None,
    ) -> Iterator[DataTemplate]:
        """
        Lists data template entities with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        name : Union[str, None], optional
            The name of the data template to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Iterator[DataTemplate]
            An iterator of DataTemplate objects.
        """

        def deserialize(items: list[dict]) -> list[DataTemplate]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        params = {
            "limit": limit,
            "offset": offset,
            "order": OrderBy(order_by).value if order_by else None,
            "text": name,
            "userId": user_id,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            deserialize=deserialize,
            params=params,
        )

    def update(self, *, data_template: DataTemplate) -> DataTemplate:
        raise NotImplementedError("Data templates cannot be updated yet.")

    def delete(self, *, id: str) -> None:
        self.session.delete(f"{self.base_path}/{id}")
