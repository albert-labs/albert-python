import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.custom_fields import CustomField, ServiceType
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class CustomFieldCollection(BaseCollection):
    _updatable_attributes = {
        "display_name",
        "searchable",
        "hidden",
        "lookup_column",
        "lookup_row",
        "min",
        "max",
        "entity_categories",
    }
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CasCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CustomFieldCollection._api_version}/customfields"

    def get_by_id(self, *, id: str) -> CustomField:
        response = self.session.get(f"{self.base_path}/{id}")
        return CustomField(**response.json())

    def get_by_name(self, *, name: str) -> CustomField | None:
        for custom_field in self.list(name=name):
            if custom_field.name.lower() == name.lower():
                return custom_field
        return None

    def list(
        self,
        *,
        name: str | None = None,
        service: ServiceType | None = None,
        lookup_column: bool | None = None,
        lookup_row: bool | None = None,
    ) -> Iterator[CustomField]:
        params = {
            "name": name,
            "service": service if service else None,
            "lookupColumn": json.dumps(lookup_column) if lookup_column is not None else None,
            "lookupRow": json.dumps(lookup_row) if lookup_row is not None else None,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=lambda items: [CustomField(**item) for item in items],
        )

    def create(self, *, custom_field: CustomField) -> CustomField:
        response = self.session.post(
            self.base_path,
            json=custom_field.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return CustomField(**response.json())

    def update(self, *, custom_field: CustomField) -> CustomField:
        """
        Update a CustomField item.
        """
        # fetch current object state
        current_object = self.get_by_id(id=custom_field.id)

        # generate the patch payload
        payload = self._generate_patch_payload(
            existing=current_object,
            updated=custom_field,
            generate_metadata_diff=False,
            stringify_values=False,
        )

        for patch in payload.data:
            if patch.attribute in ("hidden", "search") and patch.operation == "add":
                patch.operation = "update"
                patch.old_value = False

        # run patch
        url = f"{self.base_path}/{custom_field.id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))
        updated_ctf = self.get_by_id(id=custom_field.id)
        return updated_ctf
