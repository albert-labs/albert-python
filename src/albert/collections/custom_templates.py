from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import CustomTemplateId
from albert.exceptions import AlbertHTTPError
from albert.resources.custom_templates import CustomTemplate, CustomTemplateSearchItem


class CustomTemplatesCollection(BaseCollection):
    """CustomTemplatesCollection is a collection class for managing CustomTemplate entities in the Albert platform."""

    # _updatable_attributes = {"symbol", "synonyms", "category"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CustomTemplatesCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CustomTemplatesCollection._api_version}/customtemplates"

    def get_by_id(self, *, id: CustomTemplateId) -> CustomTemplate:
        """Get a Custom Template by ID

        Parameters
        ----------
        id : str
            id of the custom template

        Returns
        -------
        CustomTemplate
            The CutomTemplate with the provided ID
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return CustomTemplate(**response.json())

    def search(
        self,
        *,
        text: str | None = None,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[CustomTemplateSearchItem]:
        """
        Search for CustomTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Text to filter search results by.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Offset to begin pagination at. Default is 0.

        Returns
        -------
        Iterator[CustomTemplateSearchItem]
            An iterator of CustomTemplateSearchItem items.
        """
        params = {
            "text": text,
            "offset": offset,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                CustomTemplateSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    def create(self, *, custom_template: list[CustomTemplate]) -> list[CustomTemplate]:
        """Creates a new custom template.

        Parameters
        ----------
        custom_template : CustomTemplate
            The custom template to create.

        Returns
        -------
        CustomTemplate
            The created CustomTemplate object.
        """

        response = self.session.post(
            url=self.base_path,
            json=[
                custom_template.model_dump(
                    mode="json", by_alias=True, exclude_unset=True, exclude_none=True
                )
            ],
        )
        obj = response.json()[0]
        tags = (obj.get("Data")).get("Tags") or []

        def _resolve_tags(tid: str) -> dict:
            r = self.session.get(url=f"/api/v3/tags/{tid}")
            if r.ok:
                d = r.json()
                item = (d.get("Items") or [d])[0] if isinstance(d, dict) and "Items" in d else d
                return {"albertId": item.get("albertId", tid), "name": item.get("name")}
            return {"albertId": tid}

        if tags:
            obj["Data"]["Tags"] = [_resolve_tags(t.get("id")) for t in tags]

        return CustomTemplate(**obj)

    def get_all(
        self,
        *,
        text: str | None = None,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[CustomTemplate]:
        """
        Retrieve fully hydrated CustomTemplate entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Parameters
        ----------
        text : str, optional
            Text filter for template name or content.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Offset for search pagination.

        Returns
        -------
        Iterator[CustomTemplate]
            An iterator of CustomTemplate entities.
        """
        for item in self.search(text=text, max_items=max_items, offset=offset):
            try:
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating custom template {item.id}: {e}")

    def delete(self, *, id: CustomTemplateId) -> None:
        """
        Delete a Custom Template by ID.

        Parameters
        ----------
        id : str
            The Albert ID of the custom template to delete.

        Raises
        ------
        AlbertHTTPError
            If the API responds with a non-2xx status (e.g., 404 if not found).
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def update(self, *, custom_template: CustomTemplate) -> CustomTemplate:
        """Updates a custom template.

        Parameters
        ----------
        custom_template : CustomTemplate
            The CustomTemplate object to update. The ID must be set and matching the ID of the CustomTemplate to update.

        Returns
        -------
        CustomTemplate
            The updated CustomTemplate object.
        """

        if not custom_template.id:
            raise ValueError("CustomTemplate must have an ID to update")

        existing = self.get_by_id(id=custom_template.id)

        # Generate custom template specific patch payload
        patch_data = self._generate_custom_template_patch(
            existing=existing, updated=custom_template
        )

        if patch_data:
            path = self.base_path
            patch_json = [{"id": existing.id, "data": patch_data}]
            self.session.patch(path, json=patch_json)

        return self.get_by_id(id=custom_template.id)

    def _generate_custom_template_patch(
        self, *, existing: CustomTemplate, updated: CustomTemplate
    ) -> list[dict]:
        """Generate patch payload specifically for CustomTemplate Data attribute.

        Parameters
        ----------
        existing : CustomTemplate
            The existing template
        updated : CustomTemplate
            The updated template

        Returns
        -------
        list[dict]
            List of patch operations
        """
        patch_operations = []

        # Build the old value (existing Data)
        old_value = self._serialize_template_data(existing)

        # Build the new value (updated Data)
        new_value = self._serialize_template_data(updated)

        # Create the patch operation for the Data attribute
        if old_value != new_value:
            patch_operations.append(
                {
                    "operation": "update",
                    "attribute": "Data",
                    "oldValue": old_value,
                    "newValue": new_value,
                }
            )

        return patch_operations

    def _serialize_template_data(self, template: CustomTemplate) -> dict:
        """Serialize CustomTemplate data for patch payload.

        Parameters
        ----------
        template : CustomTemplate
            The template to serialize

        Returns
        -------
        dict
            Serialized template data
        """
        if not template.data:
            return {}

        data_dict = template.data.model_dump(mode="json", by_alias=True, exclude_none=True)

        # Process blocks with workflows and combinations
        if "Blocks" in data_dict and data_dict["Blocks"]:
            processed_blocks = []
            for block in data_dict["Blocks"]:
                processed_block = {}

                # Add Datatemplate references
                if "Datatemplate" in block:
                    processed_block["Datatemplate"] = [
                        {"id": dt["id"]} if isinstance(dt, dict) else {"id": dt}
                        for dt in block["Datatemplate"]
                    ]

                # Add Workflow with combinations
                if "Workflow" in block:
                    workflow_list = []
                    for wf in block["Workflow"]:
                        wf_dict = {"id": wf.get("id") if isinstance(wf, dict) else wf}

                        # Include combinations if present
                        if isinstance(wf, dict) and "Combination" in wf:
                            wf_dict["Combination"] = wf["Combination"]

                        workflow_list.append(wf_dict)

                    processed_block["Workflow"] = workflow_list

                processed_blocks.append(processed_block)

            data_dict["Blocks"] = processed_blocks

        # Clean up Tags to only include id
        if "Tags" in data_dict and data_dict["Tags"]:
            data_dict["Tags"] = [
                {"id": tag["id"] if isinstance(tag, dict) else tag} for tag in data_dict["Tags"]
            ]

        # Clean up entity links to only include id
        for field in ["AssignedTo", "Location", "Project"]:
            if field in data_dict and data_dict[field]:
                if isinstance(data_dict[field], dict):
                    data_dict[field] = {"id": data_dict[field].get("id")}

        # Handle Metadata if present
        if "Metadata" in data_dict and data_dict["Metadata"]:
            # Metadata should already be in the correct format from model_dump
            pass

        # Handle EntityType if present
        if "EntityType" in data_dict and data_dict["EntityType"]:
            if isinstance(data_dict["EntityType"], dict):
                data_dict["EntityType"] = {"id": data_dict["EntityType"].get("id")}

        return data_dict
