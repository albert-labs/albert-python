"""Vocabulary shared by every contract module.

Expected outcomes are written by hand from policy names and descriptions, FGC level
names, class semantics in the product spec, and product decisions recorded on SDK-216.
They are never derived from backend source or a policy's operation list.
"""

from dataclasses import dataclass, field
from enum import Enum


class Verb(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SHARE = "share"


class Expect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    UNDECIDED = "undecided"


class Module(str, Enum):
    PROJECTS = "projects"
    FORMULAS = "formulas"
    PRICING = "pricing"
    TASKS = "tasks"
    INVENTORY = "inventory"
    LOTS = "lots"
    CAS = "cas"
    UNITS = "units"
    PARAMETER_GROUPS = "parameter_groups"
    DATA_TEMPLATES = "data_templates"
    LISTS = "lists"
    TECHNOLOGY_LISTS = "technology_lists"
    NOTES = "notes"
    LOCATIONS = "locations"
    REPORTS = "reports"
    USERS = "users"
    ROLES = "roles"
    TEMPLATES = "templates"
    SDS = "sds"
    TEAMS = "teams"
    BREAKTHROUGH = "breakthrough"
    ATTRIBUTES = "attributes"
    ASK_ALBERT = "ask_albert"
    SKILLS = "skills"
    TENANT_VIEWS = "tenant_views"
    DATA_SCIENCE = "data_science"
    AUDIT = "audit"


R, C, U, D, S = Verb.READ, Verb.CREATE, Verb.UPDATE, Verb.DELETE, Verb.SHARE
RCU = frozenset({R, C, U})
RCUD = frozenset({R, C, U, D})
RU = frozenset({R, U})
RO = frozenset({R})

UNDECIDED_REASON = "contract undecided: ask product"


@dataclass(frozen=True)
class PolicyContract:
    """What one policy grants, read from its name and description."""

    id: str
    name: str
    description: str
    grants: dict[Module, frozenset[Verb]]
    undecided: dict[Module, frozenset[Verb]] = field(default_factory=dict)
    optional: bool = False
    note: str = ""

    def expect(self, module: Module, verb: Verb) -> Expect:
        if verb in self.undecided.get(module, frozenset()):
            return Expect.UNDECIDED
        if verb in self.grants.get(module, frozenset()):
            return Expect.ALLOW
        return Expect.DENY
