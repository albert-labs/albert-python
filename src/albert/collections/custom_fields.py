from albert.collections.base import BaseCollection
from albert.resources.custom_fields import CustomField, ServiceType
from albert.session import AlbertSession


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

    def _list_generator(
        self,
        *,
        limit: int = 100,
        start_key: str = None,
        name: str = None,
        service: ServiceType = None,
        lookup_column: bool = None,
        lookup_row: bool = None,
    ):
        params = {
            "limit": limit,
            "startKey": start_key,
            "name": name,
            "service": service,
            "lookupColumn": lookup_column,
            "lookupRow": lookup_row,
        }
        params = {k: v for k, v in params.items() if v is not None}
        while True:
            response = self.session.get(self.base_path, params=params)
            data = response.json().get("Items", [])
            if not data or data == []:
                break
            for item in data:
                yield CustomField(**item)
            start_key = response.json().get("lastKey", None)
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        name: str = None,
        service: ServiceType = None,
        lookup_column: bool = None,
        lookup_row: bool = None,
    ):
        return self._list_generator(
            name=name, service=service, lookup_column=lookup_column, lookup_row=lookup_row
        )

    def get_by_id(self, *, id: str):
        response = self.session.get(f"{self.base_path}/{id}")
        return CustomField(**response.json())

    def get_by_name(self, *, name: str):
        for custom_field in self.list(name=name):
            if custom_field.name.lower() == name.lower():
                return custom_field
        return None

    def create(self, *, custom_field: CustomField, avoid_duplicates: bool = True):
        # post new customfield
        response = self.session.post(
            self.base_path, json=custom_field.model_dump(by_alias=True, exclude_none=True)
        )
        return CustomField(**response.json())

    def update(self, *, updated_object: CustomField) -> CustomField:
        """
        Update a CustomField item.
        """
        # fetch current object state
        current_object = self.get_by_id(id=updated_object.id)

        # generate the patch payload
        payload = self._generate_patch_payload(
            existing=current_object,
            updated=updated_object,
            generate_metadata_diff=False,
            stringify_values=False,
        )

        # run patch
        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))
        updated_ctf = self.get_by_id(id=updated_object.id)
        return updated_ctf
