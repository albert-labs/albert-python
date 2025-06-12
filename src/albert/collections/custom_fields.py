import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.custom_fields import CustomField, ServiceType
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class CustomFieldCollection(BaseCollection):
    """
    CustomFieldCollection is a collection class for managing CustomField entities in the Albert platform.

    This collection provides methods to create, update, retrieve, and list custom fields.
    CustomFields allow you to store custom metadata on a `Project`, `InventoryItem`, `User`, `BaseTask` (Tasks), and `Lot`.

    The `FieldType` used determines the shape of the metadata field's value.
    If the `FieldType` is `LIST`, then the `FieldCategory` defines the ACL needed to add new allowed items to the given list:

    - `FieldCategory.USER_DEFINED`: allows general users to add items
    - `FieldCategory.BUSINESS_DEFINED`: only admins can add new items to the list

    Example
    --------

    ```python
    # Creating some custom fields
    from albert import Albert
    from albert.resources.custom_fields import CustomField, FieldCategory, FieldType, ServiceType
    from albert.resources.lists import ListItem
    from albert.resources.project import Project

    # Initialize the Albert client
    client = Albert()

    # Define the custom fields
    stage_gate_field = CustomField(
        name="stage_gate_status",
        display_name="Stage Gate",
        field_type=FieldType.LIST,
        service=ServiceType.PROJECTS,
        min=1,
        max=1,
        category=FieldCategory.BUSINESS_DEFINED  # Defined by the business
    )
    justification_field = CustomField(
        name="justification",
        display_name="Project Justification",
        field_type=FieldType.STRING,
        service=ServiceType.PROJECTS,
    )

    # Create the custom fields
    client.custom_fields.create(custom_field=stage_gate_field)
    client.custom_fields.create(custom_field=justification_field)
    ```
    """

    _updatable_attributes = {
        "display_name",
        "searchable",
        "hidden",
        "lookup_column",
        "lookup_row",
        "min",
        "max",
        "entity_categories",
        # "required",
        # "multiselect",
        # "pattern",
        # "default",
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
        """Get a CustomField item by its ID.

        Parameters
        ----------
        id : str
            The ID of the CustomField item.

        Returns
        -------
        CustomField
            The CustomField item.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return CustomField(**response.json())

    def get_by_name(self, *, name: str, service: ServiceType | None = None) -> CustomField | None:
        """Get a CustomField item by its name.

        Parameters
        ----------
        name : str
            The name of the CustomField item.
        service : ServiceType | None, optional
            The service the field relates to, by default None

        Returns
        -------
        CustomField | None
            The CustomField item, or None if not found.
        """
        for custom_field in self.list(name=name, service=service):
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
        """Searches for CustomField items based on the provided parameters.

        Parameters
        ----------
        name : str | None, optional
            The name of the field, by default None
        service : ServiceType | None, optional
            The related service the field is in, by default None
        lookup_column : bool | None, optional
            Whether the field relates to a lookup column, by default None
        lookup_row : bool | None, optional
            Whether the field relates to a lookup row, by default None

        Yields
        ------
        Iterator[CustomField]
            Returns an iterator of CustomField items matching the search criteria.
        """
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
        """Create a new CustomField item.

        Parameters
        ----------
        custom_field : CustomField
            The CustomField item to create.

        Returns
        -------
        CustomField
            The created CustomField item with its ID.
        """
        response = self.session.post(
            self.base_path,
            json=custom_field.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return CustomField(**response.json())

    def update(self, *, custom_field: CustomField) -> CustomField:
        """Update a CustomField item.

        Parameters
        ----------
        custom_field : CustomField
            The updated CustomField item. The ID must be set and match the Field you want to update.

        Returns
        -------
        CustomField
            The updated CustomField item as registered in Albert.
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
            if (
                patch.attribute in ("hidden", "search", "lkpColumn", "lkpRow")
                and patch.operation == "add"
            ):
                patch.operation = "update"
                patch.old_value = False
            if (
                patch.attribute in ("entityCategory")
                and patch.operation == "add"
                and isinstance(patch.new_value, list)
            ):
                patch.new_value = patch.new_value[0]

        # run patch
        url = f"{self.base_path}/{custom_field.id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))
        updated_ctf = self.get_by_id(id=custom_field.id)
        return updated_ctf
