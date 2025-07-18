from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass, Status
from albert.core.shared.identifiers import NotebookId
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


class DataTemplateInventory(EntityLink):
    batch_size: float | None = Field(default=None, alias="batchSize")
    sheet: list[Sheet | EntityLink] | None = Field(default=None)
    category: InventoryCategory | None = Field(default=None)


class DesignLink(EntityLink):
    type: DesignType


class TemplateCategory(str, Enum):
    PROPERTY_LIST = "Property Task"
    PROPERTY = "Property"
    BATCH = "Batch"
    SHEET = "Sheet"
    NOTEBOOK = "Notebook"
    GENERAL = "General"
    QC_BATCH = "BatchWithQC"


class Priority(str, Enum):
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


class JobStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    QUEUED = "queued"


class SamInput(BaseResource):
    value: str | None = Field(alias="Value", default=None)
    unit: str | None = Field(alias="Unit", default=None)
    name: str = Field(alias="Name")


class SamConfig(BaseResource):
    configuration_name: str = Field(alias="configurationName")
    configurationId: str
    machineId: str | None = Field(default=None)
    input: list[SamInput] | None = Field(default=None)
    job_status: JobStatus | None = Field(default=None, alias="status")


class Workflow(BaseResource):
    id: str
    name: str
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


class SheetData(BaseTaggedResource):
    category: Literal[TemplateCategory.SHEET] = TemplateCategory.SHEET
    designs: list[DesignLink] = Field(default=None, alias="Designs")
    formula_info: list = Field(default_factory=list, alias="FormulaInfo")
    task_rows: list[EntityLink] = Field(default_factory=list, alias="TaskRows")


class NotebookData(BaseTaggedResource):
    category: Literal[TemplateCategory.NOTEBOOK] = TemplateCategory.NOTEBOOK


_CustomTemplateDataUnion = (
    PropertyData | BatchData | SheetData | NotebookData | QCBatchData | GeneralData
)
CustomTemplateData = Annotated[_CustomTemplateDataUnion, Field(discriminator="category")]


class ACLType(str, Enum):
    TEAM = "team"
    MEMBER = "member"
    OWNER = "owner"
    VIEWER = "viewer"


class TeamACL(ACL):
    type: Literal[ACLType.TEAM] = ACLType.TEAM


class OwnerACL(ACL):
    type: Literal[ACLType.OWNER] = ACLType.OWNER


class MemberACL(ACL):
    type: Literal[ACLType.MEMBER] = ACLType.MEMBER


class ViewerACL(ACL):
    type: Literal[ACLType.VIEWER] = ACLType.VIEWER


ACLEntry = Annotated[TeamACL | OwnerACL | MemberACL | ViewerACL, Field(discriminator="type")]


class TemplateACL(BaseResource):
    fgclist: list[ACLEntry] = Field(default=None)
    acl_class: str | None = Field(default=None, alias="class")


class CustomTemplate(BaseTaggedResource):
    """A custom template entity.

    Attributes
    ----------
    name : str
        The name of the template.
    id : str
        The Albert ID of the template. Set when the template is retrieved from Albert.
    category : TemplateCategory
        The category of the template. Allowed values are `Property Task`, `Property`, `Batch`, `Sheet`, `Notebook`, and `General`.
    metadata : Dict[str, str | List[EntityLink] | EntityLink] | None
        The metadata of the template. Allowed Metadata fields can be found using Custim Fields.
    data : CustomTemplateData | None
        The data of the template.
    team : List[TeamACL] | None
        The team of the template.
    acl : TemplateACL | None

    """

    name: str
    id: str = Field(alias="albertId")
    category: TemplateCategory = Field(default=TemplateCategory.GENERAL)
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
    data: CustomTemplateData | None = Field(default=None, alias="Data")
    team: list[TeamACL] | None = Field(default_factory=list)
    acl: TemplateACL | None = Field(default_factory=list, alias="ACL")

    @model_validator(mode="before")  # Must happen before construction so the data are captured
    @classmethod
    def add_missing_category(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Initialize private attributes from the incoming data dictionary before the model is fully constructed.
        """

        if "Data" in data and "category" in data and "category" not in data["Data"]:
            data["Data"]["category"] = data["category"]
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
    name: str
    id: str = Field(alias="albertId")
    created_by_name: str = Field(..., alias="createdByName")
    created_at: str = Field(..., alias="createdAt")
    category: str
    status: Status | None = None
    resource_class: SecurityClass | None = Field(default=None, alias="resourceClass")
    data: CustomTemplateSearchItemData | None = None
    acl: list[CustomTemplateSearchItemACL]
    team: list[CustomTemplateSearchItemTeam]
