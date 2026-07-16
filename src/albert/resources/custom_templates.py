from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass, Status
from albert.core.shared.identifiers import CustomTemplateId, EntityTypeId, NotebookId
from albert.core.shared.models.base import BaseResource, EntityLink
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.inventory import InventoryCategory
from albert.resources.locations import Location
from albert.resources.projects import Project
from albert.resources.sheets import DesignType, Sheet
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tasks import TaskSource
from albert.resources.users import User, UserClass


class CustomTemplateInventoryLot(BaseAlbertModel):
    """A lot reference within a custom template inventory entry.

    Attributes
    ----------
    id : str
        The Albert ID of the lot.
    barcode : str | None
        The barcode of the lot.
    """

    id: str
    barcode: str | None = None


class DataTemplateInventory(EntityLink):
    """An inventory item reference within a custom template, with batch and lot details.

    Attributes
    ----------
    id : str
        The Albert ID of the inventory item.
    batch_size : float | None
        The batch size to use for this inventory item.
    sheet : list[Sheet | EntityLink] | None
        Sheets associated with this inventory item in the template.
    category : InventoryCategory | None
        The inventory category of the item.
    lots : list[CustomTemplateInventoryLot] | None
        Lots associated with this inventory item in the template.
    """

    batch_size: float | None = Field(default=None, alias="batchSize")
    sheet: list[Sheet | EntityLink] | None = Field(default=None)
    category: InventoryCategory | None = Field(default=None)
    lots: list[CustomTemplateInventoryLot] | None = Field(default=None, alias="Lots")


class DesignLink(EntityLink):
    """A link to a worksheet design with its type.

    Attributes
    ----------
    id : str
        The Albert ID of the design.
    type : DesignType
        The design type (apps, products, results, or process).
    """

    type: DesignType


class TemplateEntityType(BaseAlbertModel):
    """The entity type associated with a custom template.

    Attributes
    ----------
    id : EntityTypeId | None
        The Albert ID of the entity type.
    custom_category : str | None
        A custom category name for the entity type.
    """

    id: EntityTypeId | None = Field(default=None)
    custom_category: str | None = Field(default=None, alias="customCategory")


class TemplateCategory(str, Enum):
    """The kind of entity a custom template configures.

    Attributes
    ----------
    PROPERTY_LIST : str
        A property task template (``"Property Task"``).
    PROPERTY : str
        A property (measurement) template.
    BATCH : str
        A batch (formulation) task template.
    SHEET : str
        A worksheet template.
    NOTEBOOK : str
        A notebook template.
    GENERAL : str
        A general task template.
    QC_BATCH : str
        A batch task template with quality-control steps (``"BatchWithQC"``).
    """

    PROPERTY_LIST = "Property Task"
    PROPERTY = "Property"
    BATCH = "Batch"
    SHEET = "Sheet"
    NOTEBOOK = "Notebook"
    GENERAL = "General"
    QC_BATCH = "BatchWithQC"


class Priority(str, Enum):
    """The priority assigned to a task created from a template.

    Attributes
    ----------
    LOW : str
        Low priority.
    MEDIUM : str
        Medium priority.
    HIGH : str
        High priority.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class GeneralData(BaseTaggedResource):
    category: Literal[TemplateCategory.GENERAL] = TemplateCategory.GENERAL
    name: str | None = Field(default=None)
    project: SerializeAsEntityLink[Project] | None = Field(alias="Project", default=None)
    location: SerializeAsEntityLink[Location] | None = Field(alias="Location", default=None)
    assigned_to: SerializeAsEntityLink[User] | None = Field(alias="AssignedTo", default=None)
    notebook_id: NotebookId | None = Field(alias="notebookId", default=None)
    priority: Priority | None = Field(default=None)
    sources: list[TaskSource] | None = Field(alias="Sources", default=None)
    parent_id: str | None = Field(alias="parentId", default=None)
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
    notes: str | None = Field(default=None)


class JobStatus(str, Enum):
    """The status of a SAM (self-automating method) configuration job.

    Attributes
    ----------
    ACTIVE : str
        The job is active.
    INACTIVE : str
        The job is inactive.
    QUEUED : str
        The job is queued to run.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    QUEUED = "queued"


class SamInput(BaseResource):
    """An input parameter for a SAM (Sample Analysis Module) configuration.

    Attributes
    ----------
    value : str | None
        The value of the input parameter.
    unit : str | None
        The unit of the input parameter.
    name : str
        The name of the input parameter.
    """

    value: str | None = Field(alias="Value", default=None)
    unit: str | None = Field(alias="Unit", default=None)
    name: str = Field(alias="Name")


class SamConfig(BaseResource):
    """A SAM (Sample Analysis Module) machine configuration.

    Attributes
    ----------
    configuration_name : str
        The name of the configuration.
    configurationId : str
        The identifier of the configuration.
    machineId : str | None
        The identifier of the machine.
    input : list[SamInput] | None
        The input parameters for this configuration.
    job_status : JobStatus | None
        The status of the SAM job.
    """

    configuration_name: str = Field(alias="configurationName")
    configurationId: str
    machineId: str | None = Field(default=None)
    input: list[SamInput] | None = Field(default=None)
    job_status: JobStatus | None = Field(default=None, alias="status")


class Workflow(BaseResource):
    """A workflow reference within a custom template.

    Attributes
    ----------
    id : str
        The Albert ID of the workflow.
    name : str | None
        The name of the workflow.
    sam_config : list[SamConfig] | None
        SAM configurations associated with this workflow, if any.
    """

    id: str
    name: str | None = Field(default=None)
    # Some workflows may have SamConfig
    sam_config: list[SamConfig] | None = Field(default=None, alias="SamConfig")


# TODO: once DTs are done allow a list of DTs with the correct field_serializer
class Block(BaseTaggedResource):
    workflow: list[Workflow] = Field(default=None, alias="Workflow")
    datatemplate: list[EntityLink] | None = Field(default=None, alias="Datatemplate")


# TODO: once Workflows are done, add the option to have a list of Workflow objects (with the right field_serializer)
class QCBatchData(BaseTaggedResource):
    category: Literal[TemplateCategory.QC_BATCH] = TemplateCategory.QC_BATCH
    project: SerializeAsEntityLink[Project] | None = Field(alias="Project", default=None)
    inventories: list[DataTemplateInventory] | None = Field(default=None, alias="Inventories")
    workflow: list[EntityLink] = Field(default=None, alias="Workflow")
    location: SerializeAsEntityLink[Location] | None = Field(alias="Location", default=None)
    batch_size_unit: str | None = Field(alias="batchSizeUnit", default=None)
    batch_size: str | None = Field(alias="batchSize", default=None)
    priority: Priority  # enum?!
    name: str | None = Field(default=None)


class BatchData(BaseTaggedResource):
    # To Do once Workflows are done, add the option to have a list of Workflow objects (with the right field_serializer)
    name: str | None = Field(default=None)
    category: Literal[TemplateCategory.BATCH] = TemplateCategory.BATCH
    assigned_to: SerializeAsEntityLink[User] | None = Field(alias="AssignedTo", default=None)
    project: SerializeAsEntityLink[Project] | None = Field(alias="Project", default=None)
    location: SerializeAsEntityLink[Location] | None = Field(alias="Location", default=None)
    batch_size_unit: str = Field(alias="batchSizeUnit", default=None)
    inventories: list[DataTemplateInventory] | None = Field(default=None, alias="Inventories")
    priority: Priority  # enum?!
    workflow: list[EntityLink] = Field(default=None, alias="Workflow")
    notes: str | None = Field(default=None)
    due_date: str | None = Field(alias="dueDate", default=None)


class PropertyData(BaseTaggedResource):
    category: Literal[TemplateCategory.PROPERTY] = TemplateCategory.PROPERTY
    name: str | None = Field(default=None)
    blocks: list[Block] = Field(default_factory=list, alias="Blocks")  # Needs to be it's own class
    priority: Priority  # enum?!
    location: SerializeAsEntityLink[Location] | None = Field(alias="Location", default=None)
    assigned_to: SerializeAsEntityLink[User] | None = Field(alias="AssignedTo", default=None)
    project: SerializeAsEntityLink[Project] | None = Field(alias="Project", default=None)
    inventories: list[DataTemplateInventory] | None = Field(default=None, alias="Inventories")
    due_date: str | None = Field(alias="dueDate", default=None)
    notes: str | None = Field(default=None)


class SheetData(BaseTaggedResource):
    category: Literal[TemplateCategory.SHEET] = TemplateCategory.SHEET
    designs: list[DesignLink] = Field(default=None, alias="Designs")
    formula_info: list = Field(default_factory=list, alias="FormulaInfo")
    task_rows: list[EntityLink] = Field(default_factory=list, alias="TaskRows")


class NotebookData(BaseTaggedResource):
    id: str | None = Field(default=None, alias="albertId")
    category: Literal[TemplateCategory.NOTEBOOK] = TemplateCategory.NOTEBOOK


_CustomTemplateDataUnion = (
    PropertyData | BatchData | SheetData | NotebookData | QCBatchData | GeneralData
)
CustomTemplateData = Annotated[_CustomTemplateDataUnion, Field(discriminator="category")]


class ACLType(str, Enum):
    """The kind of access-control entry on a custom template.

    Attributes
    ----------
    TEAM : str
        A team-level access entry.
    MEMBER : str
        A member with edit access.
    OWNER : str
        An owner with full control.
    VIEWER : str
        A viewer with read-only access.
    """

    TEAM = "team"
    MEMBER = "member"
    OWNER = "owner"
    VIEWER = "viewer"


class TeamACL(ACL):
    type: Literal[ACLType.TEAM, "CustomTemplateTeam"] = ACLType.TEAM


class OwnerACL(ACL):
    type: Literal[ACLType.OWNER, "CustomTemplateOwner"] = ACLType.OWNER


class MemberACL(ACL):
    type: Literal[ACLType.MEMBER, "CustomTemplateMember"] = ACLType.MEMBER


class ViewerACL(ACL):
    type: Literal[ACLType.VIEWER, "CustomTemplateViewer"] = ACLType.VIEWER


ACLEntry = Annotated[TeamACL | OwnerACL | MemberACL | ViewerACL, Field(discriminator="type")]


class TemplateACL(BaseResource):
    """Access control settings for a custom template.

    Attributes
    ----------
    fgclist : list[ACLEntry]
        The list of access control entries (team, owner, member, viewer).
    acl_class : str | None
        The default access class for the template.
    """

    fgclist: list[ACLEntry] = Field(default=None)
    acl_class: str | None = Field(default=None, alias="class")


class CustomTemplate(BaseTaggedResource, HydrationMixin["CustomTemplate"]):
    """A reusable custom template in Albert.

    A custom template captures a standard entity setup so it can be applied
    repeatedly. Its [`category`][albert.resources.custom_templates.CustomTemplate.category] selects what kind of entity it configures
    (see [`TemplateCategory`][albert.resources.custom_templates.TemplateCategory]), and its [`data`][albert.resources.custom_templates.CustomTemplate.data] holds the category-
    specific defaults (project, location, assignee, inventories, workflow,
    priority, and so on). Manage templates through
    [`CustomTemplatesCollection`][albert.collections.custom_templates.CustomTemplatesCollection].

    Attributes
    ----------
    name : str
        The name of the template.
    id : CustomTemplateId or None
        The Custom Template ID (format ``CTP...``). Set when the template is
        retrieved from or created in Albert.
    category : TemplateCategory
        The kind of entity the template configures. Defaults to
        ``TemplateCategory.GENERAL``.
    metadata : dict[str, MetadataItem] or None
        Metadata values for the template. Allowed metadata keys are those defined
        as Custom Fields (see
        [`CustomFieldCollection`][albert.collections.custom_fields.CustomFieldCollection]).
    data : CustomTemplateData or None
        The category-specific configuration the template applies.
    entity_type : TemplateEntityType or None
        The entity type associated with the template.
    locked : bool or None
        Whether the template is locked when loaded in the UI.
    team : list[TeamACL] or None
        The teams associated with the template.
    acl : TemplateACL or None
        The access-control list governing who can use the template.

    Examples
    --------
    ```python
    from albert.resources.custom_templates import CustomTemplate, TemplateCategory
    template = CustomTemplate(
        name="Standard Property Task",
        category=TemplateCategory.PROPERTY,
    )
    ```
    """

    name: str
    id: CustomTemplateId | None = Field(default=None, alias="albertId")
    category: TemplateCategory = Field(default=TemplateCategory.GENERAL)
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
    data: CustomTemplateData | None = Field(default=None, alias="Data")
    entity_type: TemplateEntityType | None = Field(default=None, alias="EntityType")
    locked: bool | None = Field(default=None)
    team: list[TeamACL] | None = Field(default_factory=list)
    acl: TemplateACL | None = Field(default_factory=list, alias="ACL")

    @model_validator(mode="before")  # Must happen before construction so the data are captured
    @classmethod
    def add_missing_category(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Initialize private attributes from the incoming data dictionary before the model is fully constructed.
        """
        if not isinstance(data, dict):
            return data

        data_payload = data.get("Data")
        category = data.get("category")
        if isinstance(data_payload, dict) and category is not None:
            data_payload.setdefault("category", category)
        return data


class CustomTemplateSearchItemData(BaseAlbertModel):
    designs: list[DesignLink] = Field(default=None, alias="Designs")
    formula_info: list = Field(default_factory=list, alias="FormulaInfo")
    task_rows: list[EntityLink] = Field(default_factory=list, alias="TaskRows")


class CustomTemplateSearchItemACL(ACL):
    name: str | None = None
    user_type: UserClass | None = Field(default=None, alias="userType")
    type: ACLType


class CustomTemplateSearchItemTeam(BaseAlbertModel):
    id: str
    name: str
    type: ACLType | None = None
    fgc: AccessControlLevel | None = Field(default=None)


class CustomTemplateSearchItem(BaseAlbertModel, HydrationMixin[CustomTemplate]):
    """A lightweight custom template returned by search.

    Returned by
    [`search`][albert.collections.custom_templates.CustomTemplatesCollection.search],
    this is a partially populated view of a template optimized for fast lookups.
    Hydrate it (or call
    [`get_by_id`][albert.collections.custom_templates.CustomTemplatesCollection.get_by_id])
    to obtain the full [`CustomTemplate`][albert.resources.custom_templates.CustomTemplate].

    Attributes
    ----------
    name : str
        The name of the template.
    id : CustomTemplateId
        The Custom Template ID (format ``CTP...``).
    created_by_name : str
        The display name of the user who created the template.
    created_at : str
        When the template was created.
    category : str or None
        The template category.
    status : Status or None
        The template's status.
    resource_class : SecurityClass or None
        The security classification of the template.
    data : CustomTemplateSearchItemData or None
        Partial template data included in search results.
    acl : list[CustomTemplateSearchItemACL] or None
        The access-control entries on the template.
    team : list[CustomTemplateSearchItemTeam] or None
        The teams associated with the template.
    """

    name: str
    id: CustomTemplateId = Field(alias="albertId")
    created_by_name: str = Field(..., alias="createdByName")
    created_at: str = Field(..., alias="createdAt")
    category: str | None = None
    status: Status | None = None
    resource_class: SecurityClass | None = Field(default=None, alias="resourceClass")
    data: CustomTemplateSearchItemData | None = None
    acl: list[CustomTemplateSearchItemACL] | None = None
    team: list[CustomTemplateSearchItemTeam] | None = None
