from __future__ import annotations

import os

from pydantic import SecretStr

from albert.collections.activities import ActivityCollection
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
from albert.collections.report_templates import ReportTemplateCollection
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
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.core.session import AlbertSession


class Albert:
    """
    Main client for interacting with the Albert API.

    This class manages authentication and access to API resource collections.
    It supports token-based, SSO, and client credentials authentication via a unified interface.

    Parameters
    ----------
    base_url : str, optional
        The base URL of the Albert API. Defaults to the "ALBERT_BASE_URL" environment variable
        or "https://app.albertinvent.com" if not set.
    token : str, optional
        A static token for authentication. If provided, it overrides any `auth_manager`.
        Defaults to the "ALBERT_TOKEN" environment variable.
    auth_manager : AlbertClientCredentials | AlbertSSOClient, optional
        An authentication manager for OAuth2-based authentication flows.
        Ignored if `token` is provided.
    retries : int, optional
        Maximum number of retries for failed HTTP requests.
    session : AlbertSession, optional
        A fully configured session instance. If provided, `base_url`, `token`, and `auth_manager`
        are all ignored.

    Attributes
    ----------
    session : AlbertSession
        The internal session used for authenticated requests.
    projects : ProjectCollection
        Access to project-related API methods.
    tags : TagCollection
        Access to tag-related API methods.
    inventory : InventoryCollection
        Access to inventory-related API methods.
    companies : CompanyCollection
        Access to company-related API methods.

    Helpers
    -------------------
    - `from_token` — Create a client using a static token.
    - `from_sso` — Create a client using interactive browser-based SSO login.
    - `from_client_credentials` — Create a client using OAuth2 client credentials.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
        retries: int | None = None,
        session: AlbertSession | None = None,
    ):
        self.session = session or AlbertSession(
            base_url=base_url or os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com",
            token=token or os.getenv("ALBERT_TOKEN"),
            auth_manager=auth_manager,
            retries=retries,
        )

    @classmethod
    def from_token(cls, *, base_url: str, token: str) -> Albert:
        """Create an Albert client using a static token for authentication."""
        return cls(base_url=base_url, token=token)

    @classmethod
    def from_sso(
        cls,
        *,
        base_url: str,
        email: str,
        port: int = 5000,
        tenant_id: str | None = None,
        retries: int | None = None,
    ) -> Albert:
        """Create an Albert client using interactive OAuth2 SSO login."""
        oauth = AlbertSSOClient(base_url=base_url, email=email)
        oauth.authenticate(minimum_port=port, tenant_id=tenant_id)
        return cls(base_url=base_url, auth_manager=oauth, retries=retries)

    @classmethod
    def from_client_credentials(
        cls,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        retries: int | None = None,
    ) -> Albert:
        """Create an Albert client using client credentials authentication."""
        creds = AlbertClientCredentials(
            id=client_id,
            secret=SecretStr(client_secret),
            base_url=base_url,
        )
        return cls(base_url=base_url, auth_manager=creds, retries=retries)

    @property
    def projects(self) -> ProjectCollection:
        return ProjectCollection(session=self.session)

    @property
    def activities(self) -> ActivityCollection:
        return ActivityCollection(session=self.session)

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
    def report_templates(self) -> ReportTemplateCollection:
        return ReportTemplateCollection(session=self.session)

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
    def custom_templates(self) -> CustomTemplatesCollection:
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

    @property
    def btmodels(self) -> BTModelCollection:
        return BTModelCollection(session=self.session)

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
