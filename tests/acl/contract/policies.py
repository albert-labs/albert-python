"""Policy contract: one entry per policy, with grants read from its description.

Names and descriptions are copied verbatim from the live policy catalog
(``getPolicies``). The ``grants`` column is a hand reading of the description plus the
SDK-216 decisions:

- Sharing needs a Full policy (and an owner-level FGC on the record); Edit never shares.
- Bulk delete and project delete are admin-only for every policy.
- CAS/Units/Lists/Locations delete is admin-only (interim), so Full == Edit there.
- "Edit ... but not able to create" means R+U only.
"""

from tests.acl.contract.model import (
    RCU,
    RCUD,
    RO,
    RU,
    C,
    D,
    Module,
    PolicyContract,
    R,
    S,
    U,
)

M = Module

POLICIES: tuple[PolicyContract, ...] = (
    PolicyContract(
        "ProjectsViewAccess",
        "Projects View Access",
        "Ability to view projects",
        {M.PROJECTS: RO},
    ),
    PolicyContract(
        "ProjectsEditAccess",
        "Projects Edit Access",
        "Ability to view and edit projects, but not able to create new projects",
        {M.PROJECTS: RU},
    ),
    PolicyContract(
        "ProjectsFullAccess",
        "Projects Full Access",
        "Ability to view, create, edit, and delete project content. "
        "Deleting a project itself is admin-only.",
        {M.PROJECTS: frozenset({R, C, U, S})},
        note="project delete is admin-only; project content delete is per-module",
    ),
    PolicyContract(
        "FormulaViewAccess",
        "Formula View Access",
        "Ability to view formulas",
        {M.FORMULAS: RO},
    ),
    PolicyContract(
        "FormulaEditAccess",
        "Formula Edit Access",
        "Ability to view, create, and edit formulas. Formulas inherit the parent project's "
        "ACL; deleting a formula requires delete rights on its project.",
        {M.FORMULAS: RCU},
    ),
    PolicyContract(
        "FormulaFullAccess",
        "Formula Full Access",
        "Ability to view, create, and edit formulas. Formula deletion is governed by the "
        "parent project's ACL.",
        {M.FORMULAS: RCU},
    ),
    PolicyContract(
        "PricingViewAccess",
        "Pricing View Access",
        "Ability to view Inventory Pricing",
        {M.PRICING: RO},
    ),
    PolicyContract(
        "PricingEditAccess",
        "Pricing Edit Access",
        "Ability to view, create, and edit inventory pricing. Deleting pricing requires "
        "Pricing Full Access.",
        {M.PRICING: RCU},
    ),
    PolicyContract(
        "PricingFullAccess",
        "Pricing Full Access",
        "Ability to view, create, edit, and delete inventory pricing.",
        {M.PRICING: RCUD},
    ),
    PolicyContract("TasksViewAccess", "Tasks View Access", "Ability to view tasks", {M.TASKS: RO}),
    PolicyContract(
        "TasksEditAccess",
        "Tasks Edit Access",
        "Ability to view, create, and edit tasks. Deleting tasks requires Tasks Full Access. "
        "Batch tasks also follow the parent project's ACL.",
        {M.TASKS: RCU},
    ),
    PolicyContract(
        "TasksFullAccess",
        "Tasks Full Access",
        "Ability to view, create, edit, and delete tasks. Batch tasks also follow the parent "
        "project's ACL.",
        {M.TASKS: frozenset({R, C, U, D, S})},
    ),
    PolicyContract(
        "InventoryViewAccess",
        "Inventory View Access",
        "Ability to view all Inventory",
        {M.INVENTORY: RO, M.LOTS: RO},
    ),
    PolicyContract(
        "InventoryAccess",
        "Inventory Access (non-formula)",
        "Ability to view, create, and edit non-formula inventory. Deleting inventory requires "
        "Inventory Full Access; formula inventory inherits the parent project's ACL.",
        {M.INVENTORY: RCU, M.LOTS: RCU},
    ),
    PolicyContract(
        "InventoryFullAccess",
        "Inventory Full Access",
        "Ability to view, create, edit, and delete non-project-specific inventory, and their "
        "lots. Project-wide inventory cleanup runs as part of project delete.",
        {M.INVENTORY: frozenset({R, C, U, D, S}), M.LOTS: RCUD},
    ),
    PolicyContract(
        "CASEditAccess",
        "CAS Edit Access",
        "Ability to view, create, and edit CAS entries. Deleting CAS requires CAS Full Access.",
        {M.CAS: RCU},
    ),
    PolicyContract(
        "CASFullAccess",
        "CAS Full Access",
        "Ability to view, create, and edit CAS entries. Deleting CAS is admin-only (interim).",
        {M.CAS: RCU},
    ),
    PolicyContract(
        "UnitsEditAccess",
        "Units Edit Access",
        "Ability to view, create, and edit units and unit families. Deleting units requires "
        "Unit Full Access.",
        {M.UNITS: RCU},
    ),
    PolicyContract(
        "UnitsFullAccess",
        "Unit Full Access",
        "Ability to view, create, and edit units and unit families. Deleting units is "
        "admin-only (interim).",
        {M.UNITS: RCU},
    ),
    PolicyContract(
        "InventoryEditAccess",
        "Inventory Edit Access",
        "Ability to view and edit inventory items (except all project-specific inventory). "
        "Also grants editing of their lots.",
        {M.INVENTORY: RU, M.LOTS: RU},
    ),
    PolicyContract(
        "ParameterGroupsViewAccess",
        "Parameter Groups View Access",
        "Ability to view all parameter groups",
        {M.PARAMETER_GROUPS: RO},
    ),
    PolicyContract(
        "ParameterGroupsEditAccess",
        "Parameter Groups Edit Access",
        "Ability to view and edit parameter groups, but not able to create new parameter groups",
        {M.PARAMETER_GROUPS: RU},
    ),
    PolicyContract(
        "ParameterGroupsFullAccess",
        "Parameter Groups Full Access",
        "Ability to view, edit, create, and delete parameter groups",
        {M.PARAMETER_GROUPS: RCUD},
    ),
    PolicyContract(
        "DataTemplatesViewAccess",
        "Data Templates View Access",
        "Ability to view all data templates",
        {M.DATA_TEMPLATES: RO},
    ),
    PolicyContract(
        "DataTemplatesEditAccess",
        "Data Templates Edit Access",
        "Ability to view and edit data templates, but not able to create new data templates",
        {M.DATA_TEMPLATES: RU},
    ),
    PolicyContract(
        "DataTemplatesFullAccess",
        "Data Templates Full Access",
        "Ability to view, edit, create, and delete data templates",
        {M.DATA_TEMPLATES: RCUD},
    ),
    PolicyContract(
        "ListsEditAccess",
        "Lists Edit Access",
        "Ability to view, create, and edit user-managed lists. Deleting lists requires User "
        "Managed Lists Full Access.",
        {M.LISTS: RCU},
    ),
    PolicyContract(
        "ListsFullAccess",
        "User Managed Lists Full Access",
        "Ability to view, create, and edit user-managed lists. Deleting lists is admin-only "
        "(interim).",
        {M.LISTS: RCU},
    ),
    PolicyContract(
        "TechnologyFullAccess",
        "Company Managed Lists Full Access",
        "Ability to view, edit, create, and delete Technology Lists",
        {M.TECHNOLOGY_LISTS: RCUD},
        note="technology lists only; must not delete user-managed lists",
    ),
    PolicyContract(
        "NotesFullAccess",
        "Notes Full Access",
        "Ability to view, edit, create, and delete Notes",
        {M.NOTES: RCUD},
    ),
    PolicyContract(
        "LocationsEditAccess",
        "Locations Edit Access",
        "Ability to view, create, and edit locations. Deleting locations requires Locations "
        "Full Access.",
        {M.LOCATIONS: RCU},
    ),
    PolicyContract(
        "LocationsFullAccess",
        "Locations Full Access",
        "Ability to view, create, and edit locations. Deleting locations is admin-only (interim).",
        {M.LOCATIONS: RCU},
    ),
    PolicyContract(
        "ReportsViewAccess", "Reports View Access", "Ability to view all reports", {M.REPORTS: RO}
    ),
    PolicyContract(
        "ReportsEditAccess",
        "Reports Edit Access",
        "Ability to view, create, edit, and schedule reports. Deleting reports requires Reports "
        "Full Access.",
        {M.REPORTS: RCU},
    ),
    PolicyContract(
        "ReportsFullAccess",
        "Reports Full Access",
        "Ability to view, edit, create, and delete reports",
        {M.REPORTS: frozenset({R, C, U, D, S})},
    ),
    PolicyContract(
        "UsersFullAccess",
        "Users Full Access",
        "Ability to view, edit, create, and delete Users",
        {M.USERS: RCUD},
    ),
    PolicyContract("UsersViewAccess", "Users View Access", "Ability to view Users", {M.USERS: RO}),
    PolicyContract(
        "UsersEditAccess",
        "Users Edit Access",
        "Ability to view and edit users, but not able to create new users",
        {M.USERS: RU},
    ),
    PolicyContract(
        "UserRolesEditAccess",
        "User Roles Edit Access",
        "Ability to view, create, and edit roles and policies.",
        {M.ROLES: RCU},
    ),
    PolicyContract(
        "UserRolesFullAccess",
        "Access Roles Full Access",
        "Ability to view, edit, and create roles and policies",
        {M.ROLES: RCU},
        note="Full without delete is a recorded finding (SDK-216)",
    ),
    PolicyContract(
        "TemplatesViewAccess",
        "Templates View Access",
        "Ability to view Templates",
        {M.TEMPLATES: RO},
    ),
    PolicyContract(
        "TemplatesFullAccess",
        "Templates Edit Access",
        "Ability to view, create, and edit templates. Deleting templates is admin-only.",
        {M.TEMPLATES: RCU},
    ),
    PolicyContract(
        "SDSFullAccess",
        "SDS Edit Access",
        "Ability to view, create, edit, and download SDS. Deleting substances is admin-only.",
        {M.SDS: RCU},
    ),
    PolicyContract(
        "DataScience",
        "DataScience Related Access",
        "Ability to access v3 endpoints specific for DS activities",
        {M.DATA_SCIENCE: RO},
    ),
    PolicyContract(
        "Audit", "Audit Access", "Ability to access all user activities", {M.AUDIT: RO}
    ),
    PolicyContract(
        "TeamFullAccess",
        "Team Full Access",
        "Ability to view, edit, create, and inactive Team.",
        {M.TEAMS: RCUD},
    ),
    PolicyContract(
        "TeamEditAccess",
        "Team Edit Access",
        "Ability to view and edit teams, but not able to create new team",
        {M.TEAMS: RU},
    ),
    PolicyContract(
        "BreakthroughEditAccess",
        "Breakthrough Edit Access",
        "Ability to view, create, and edit Breakthrough insights, datasets, and models. "
        "Deleting them requires Breakthrough Full Access.",
        {M.BREAKTHROUGH: RCU},
    ),
    PolicyContract(
        "BreakthroughFullAccess",
        "Breakthrough Full Access",
        "Ability to view, edit, create, and delete Breakthrough",
        {M.BREAKTHROUGH: RCUD},
    ),
    PolicyContract(
        "AskAlbertFullAccess",
        "Ask Albert Full Access",
        "Ability to view, edit, create, and delete Ask Albert Services (Skills approval are "
        "reserved for admins only)",
        {M.ASK_ALBERT: RCUD},
    ),
    PolicyContract(
        "AskAlbertSkillsWriteAccess",
        "Ask Albert Skills Write Access",
        "Ability to view, edit, create and delete Ask Albert Skills",
        {M.SKILLS: RCUD},
    ),
    PolicyContract(
        "ReferenceAttributesViewAccess",
        "Attributes View Access",
        "Ability to view Attributes",
        {M.ATTRIBUTES: RO},
    ),
    PolicyContract(
        "ReferenceAttributesEditAccess",
        "Attributes Edit Access",
        "Ability to view and edit Attributes, but not able to create new Attributes",
        {M.ATTRIBUTES: RU},
    ),
    PolicyContract(
        "ReferenceAttributesFullAccess",
        "Attributes Full Access",
        "Ability to view, edit, create, and delete Attributes",
        {M.ATTRIBUTES: RCUD},
    ),
    PolicyContract(
        "TenantViewsFullAccess",
        "Tenant Views Full Access",
        "Ability to manage personal grid views and tenant default grid view templates",
        {M.TENANT_VIEWS: RCUD},
    ),
    PolicyContract(
        "AskAlbertWebSearchAccess",
        "Ask Albert: Web Search",
        "Ability to use Web Search in Ask Albert",
        {},
        optional=True,
    ),
    PolicyContract(
        "AskAlbertRegulatoryDbAccess",
        "Ask Albert: RegulatoryDB Search",
        "Ability to use RegulatoryDB Search in Ask Albert",
        {},
        optional=True,
    ),
    PolicyContract(
        "AskAlbertArtifactGenerationAccess",
        "Ask Albert: Artifact Generation",
        "Ability to use Artifact Generation in Ask Albert",
        {},
        optional=True,
    ),
    PolicyContract(
        "AskAlbertSkillsFullAccess",
        "Manage Skills Access",
        "Ability to approve, reject and demote skill promotions, and to manage every "
        "organization skill and its sharing",
        {M.SKILLS: frozenset({R, C, U, D, S})},
        optional=True,
    ),
)

BY_ID: dict[str, PolicyContract] = {p.id: p for p in POLICIES}
REQUIRED_IDS: frozenset[str] = frozenset(p.id for p in POLICIES if not p.optional)
