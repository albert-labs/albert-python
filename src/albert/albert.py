import os

from albert.collections.attachments import AttachmentCollection
from albert.collections.batch_data import BatchDataCollection
from albert.collections.btdataset import BTDatasetCollection
from albert.collections.btinsight import BTInsightCollection
from albert.collections.btmodel import BTModelCollection, BTModelSessionCollection
from albert.collections.cas import CasCollection
from albert.collections.companies import CompanyCollection
from albert.collections.custom_fields import CustomFieldCollection
from albert.collections.custom_templates import CustomTemplatesCollection
from albert.collections.data_columns import DataColumnCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.files import FileCollection
from albert.collections.inventory import InventoryCollection
from albert.collections.links import LinksCollection
from albert.collections.lists import ListsCollection
from albert.collections.locations import LocationCollection
from albert.collections.lots import LotCollection
from albert.collections.notebooks import NotebookCollection
from albert.collections.notes import NotesCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.collections.parameters import ParameterCollection
from albert.collections.pricings import PricingCollection
from albert.collections.product_design import ProductDesignCollection
from albert.collections.projects import ProjectCollection
from albert.collections.property_data import PropertyDataCollection
from albert.collections.reports import ReportCollection
from albert.collections.roles import RoleCollection
from albert.collections.storage_locations import StorageLocationsCollection
from albert.collections.substance import SubstanceCollection
from albert.collections.tags import TagCollection
from albert.collections.tasks import TaskCollection
from albert.collections.un_numbers import UnNumberCollection
from albert.collections.units import UnitCollection
from albert.collections.users import UserCollection
from albert.collections.workflows import WorkflowCollection
from albert.collections.worksheets import WorksheetCollection
from albert.session import AlbertSession
from albert.utils.credentials import ClientCredentials
from albert.utils.environment import AlbertEnvironment


class Albert:
    """
    Albert is the main client class for interacting with the Albert API.

    Parameters
    ----------
    base_url : str, optional
        The base URL of the Albert API (default is "https://app.albertinvent.com").
    environment: AlbertEnvironment, optional
        The Albert environment to use for the base URL (default is "AlbertEnvironment.APP").
    token : str, optional
        The token for authentication (default is read from environment variable "ALBERT_TOKEN").
    client_credentials: ClientCredentials, optional
        The client credentials for programmatic authentication.
        Client credentials can be read from the environment by `ClientCredentials.from_env()`.
    retries : int, optional
        The maximum number of retries for failed requests (default is None).

    Attributes
    ----------
    session : AlbertSession
        The session for API requests, with a base URL set.
    projects : ProjectCollection
        The project collection instance.
    tags : TagCollection
        The tag collection instance.
    inventory : InventoryCollection
        The inventory collection instance.
    companies : CompanyCollection
        The company collection instance.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        environment: AlbertEnvironment | None = None,
        token: str | None = None,
        client_credentials: ClientCredentials | None = None,
        retries: int | None = None,
    ):
        if environment is not None:
            base_url = environment.base_url
        else:
            base_url = base_url or os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com"
        self.session = AlbertSession(
            base_url=base_url,
            token=token or os.getenv("ALBERT_TOKEN"),
            client_credentials=client_credentials,
            retries=retries,
        )

    @property
    def projects(self) -> ProjectCollection:
        return ProjectCollection(session=self.session)

    @property
    def attachments(self) -> AttachmentCollection:
        return AttachmentCollection(session=self.session)

    @property
    def tags(self) -> TagCollection:
        return TagCollection(session=self.session)

    @property
    def inventory(self) -> InventoryCollection:
        return InventoryCollection(session=self.session)

    @property
    def companies(self) -> CompanyCollection:
        return CompanyCollection(session=self.session)

    @property
    def lots(self) -> LotCollection:
        return LotCollection(session=self.session)

    @property
    def units(self) -> UnitCollection:
        return UnitCollection(session=self.session)

    @property
    def cas_numbers(self) -> CasCollection:
        return CasCollection(session=self.session)

    @property
    def data_columns(self) -> DataColumnCollection:
        return DataColumnCollection(session=self.session)

    @property
    def data_templates(self) -> DataTemplateCollection:
        return DataTemplateCollection(session=self.session)

    @property
    def un_numbers(self) -> UnNumberCollection:
        return UnNumberCollection(session=self.session)

    @property
    def users(self) -> UserCollection:
        return UserCollection(session=self.session)

    @property
    def locations(self) -> LocationCollection:
        return LocationCollection(session=self.session)

    @property
    def lists(self) -> ListsCollection:
        return ListsCollection(session=self.session)

    @property
    def notebooks(self) -> NotebookCollection:
        return NotebookCollection(session=self.session)

    @property
    def notes(self) -> NotesCollection:
        return NotesCollection(session=self.session)

    @property
    def custom_fields(self) -> CustomFieldCollection:
        return CustomFieldCollection(session=self.session)

    @property
    def reports(self) -> ReportCollection:
        return ReportCollection(session=self.session)

    @property
    def roles(self) -> RoleCollection:
        return RoleCollection(session=self.session)

    @property
    def worksheets(self) -> WorksheetCollection:
        return WorksheetCollection(session=self.session)

    @property
    def tasks(self) -> TaskCollection:
        return TaskCollection(session=self.session)

    @property
    def templates(self) -> CustomTemplatesCollection:
        return CustomTemplatesCollection(session=self.session)

    @property
    def parameter_groups(self) -> ParameterGroupCollection:
        return ParameterGroupCollection(session=self.session)

    @property
    def parameters(self) -> ParameterCollection:
        return ParameterCollection(session=self.session)

    @property
    def property_data(self) -> PropertyDataCollection:
        return PropertyDataCollection(session=self.session)

    @property
    def product_design(self) -> ProductDesignCollection:
        return ProductDesignCollection(session=self.session)

    @property
    def storage_locations(self) -> StorageLocationsCollection:
        return StorageLocationsCollection(session=self.session)

    @property
    def pricings(self) -> PricingCollection:
        return PricingCollection(session=self.session)

    @property
    def files(self) -> FileCollection:
        return FileCollection(session=self.session)

    @property
    def workflows(self) -> WorkflowCollection:
        return WorkflowCollection(session=self.session)

    @property
    def btdatasets(self) -> BTDatasetCollection:
        return BTDatasetCollection(session=self.session)

    @property
    def btmodelsessions(self) -> BTModelSessionCollection:
        return BTModelSessionCollection(session=self.session)

    def btmodels(self, *, parent_id: str) -> BTModelCollection:
        return BTModelCollection(session=self.session, parent_id=parent_id)

    @property
    def btinsights(self) -> BTInsightCollection:
        return BTInsightCollection(session=self.session)

    @property
    def substances(self) -> SubstanceCollection:
        return SubstanceCollection(session=self.session)

    @property
    def links(self) -> LinksCollection:
        return LinksCollection(session=self.session)

    @property
    def batch_data(self) -> BatchDataCollection:
        return BatchDataCollection(session=self.session)
