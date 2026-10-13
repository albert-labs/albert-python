"""Record-level contract: FGC level x child kind -> verbs, plus class semantics.

Sources: FGC level names, PLSV-780 §3, the class matrix in the ACL functional spec, and
AN-1204 (private records are listable, not directly readable), PLSV-827 (private contents
such as documents and formulas never surface without a grant), and
Lenore's SDK-216 decisions (ProjectAllTask sees formulas and batch tasks;
ProjectViewer is the
legacy technician; a ProjectOwner may share a project, inventory sharing needs a Full
policy plus an owner-level FGC; project delete is
admin-only). Cells marked undecided are open product questions and skip with a reason.

Only batch tasks inherit project access. General and property tasks are governed by the
caller's Tasks policies, never by the parent project's FGC or class, so they have no cells
here (``POLICY_TASKS``). For the same reason ``ProjectPropertyTask`` is not a project
level: it is gated by the normal property-task policies, not by the project.
"""

from dataclasses import dataclass, field
from enum import Enum

from tests.acl.contract.model import RCU, RCUD, RO, RU, C, Expect, R, S, U, Verb


class Kind(str, Enum):
    """A record kind reachable from a project or inventory item."""

    PROJECT = "project"
    FORMULA = "formula"
    GENERAL_TASK = "general_task"
    PROPERTY_TASK = "property_task"
    BATCH_TASK = "batch_task"
    LOT = "lot"
    TASK_CHILD = "task_child"
    PROJECT_CHILD = "project_child"
    REPORT = "report"
    INVENTORY = "inventory"
    INVENTORY_CHILD = "inventory_child"


@dataclass(frozen=True)
class LevelContract:
    level: str
    grants: dict[Kind, frozenset[Verb]]
    undecided: dict[Kind, frozenset[Verb]] = field(default_factory=dict)

    def expect(self, kind: Kind, verb: Verb) -> Expect:
        if verb in self.undecided.get(kind, frozenset()):
            return Expect.UNDECIDED
        if verb in self.grants.get(kind, frozenset()):
            return Expect.ALLOW
        return Expect.DENY


K = Kind
POLICY_TASKS = frozenset({K.GENERAL_TASK, K.PROPERTY_TASK})


PROJECT_LEVELS: dict[str, LevelContract] = {
    "ProjectOwner": LevelContract(
        "ProjectOwner",
        {
            K.PROJECT: frozenset({R, U, S}),
            K.FORMULA: RCUD,
            K.BATCH_TASK: RCUD,
            K.LOT: RCUD,
            K.TASK_CHILD: RCUD,
            K.PROJECT_CHILD: RCUD,
            K.REPORT: frozenset({R, C, S}),
        },
    ),
    "ProjectEditor": LevelContract(
        "ProjectEditor",
        {
            K.PROJECT: RU,
            K.FORMULA: RCUD,
            K.BATCH_TASK: RCUD,
            K.LOT: RCUD,
            K.TASK_CHILD: RCUD,
            K.PROJECT_CHILD: RCUD,
            K.REPORT: frozenset({R, C}),
        },
    ),
    "ProjectViewer": LevelContract(
        "ProjectViewer",
        {
            K.PROJECT: RO,
            K.FORMULA: RO,
            K.BATCH_TASK: RCU,
            K.LOT: RCU,
            K.TASK_CHILD: RCUD,
            K.PROJECT_CHILD: RO,
            K.REPORT: frozenset({R, C}),
        },
    ),
    "ProjectAllTask": LevelContract(
        "ProjectAllTask",
        {
            K.PROJECT: RO,
            K.FORMULA: RO,
            K.BATCH_TASK: RCU,
            K.LOT: RCU,
            K.TASK_CHILD: RCUD,
            K.REPORT: frozenset({R, C}),
        },
        undecided={
            K.BATCH_TASK: frozenset({Verb.DELETE}),
            K.PROJECT_CHILD: frozenset({R}),
        },
    ),
    "ProjectStrictViewer": LevelContract(
        "ProjectStrictViewer",
        {
            K.PROJECT: RO,
            K.FORMULA: RO,
            K.BATCH_TASK: RO,
            K.LOT: RO,
            K.TASK_CHILD: RO,
            K.PROJECT_CHILD: RO,
            K.REPORT: frozenset({R, C}),
        },
    ),
}

INVENTORY_LEVELS: dict[str, LevelContract] = {
    "InventoryOwner": LevelContract(
        "InventoryOwner",
        {
            K.INVENTORY: frozenset({R, U, S, Verb.DELETE}),
            K.LOT: RCUD,
            K.INVENTORY_CHILD: RCUD,
        },
    ),
    "InventoryViewer": LevelContract(
        "InventoryViewer",
        {K.INVENTORY: RO, K.LOT: RO, K.INVENTORY_CHILD: RO},
        undecided={K.INVENTORY_CHILD: frozenset({R})},
    ),
}

SHARE_REQUIRES_FULL_POLICY = {K.INVENTORY: "InventoryFullAccess"}

OWNER_LEVELS = frozenset({"ProjectOwner", "InventoryOwner"})


class AccessClass(str, Enum):
    SHARED = "shared"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class ReadPath(str, Enum):
    """A separate way to read a record; each is its own action and report row."""

    GET_BY_ID = "get_by_id"
    LIST = "list"
    BULK_IDS = "bulk_ids"
    SEARCH_GET = "search_get"
    SEARCH_POST = "search_post"
    SUGGEST = "suggest"
    DOCUMENT_SEARCH = "document_search"
    LLMSEARCH = "llmsearch"
    FACETS = "facets"


DIRECT_PATHS = frozenset({ReadPath.GET_BY_ID, ReadPath.BULK_IDS})
CONTENT_PATHS = frozenset({ReadPath.DOCUMENT_SEARCH})


def class_expect(cls: AccessClass, verb: Verb, path: ReadPath | None = None) -> Expect:
    """Expected outcome for a standard user with no ACL entry on the record.

    Functional spec matrix (standard user, implicit / explicit):
    Shared I-All; Restricted I-Read/List; Private I-List; Confidential none.

    Private records appear in list and search results for every standard user (confirmed
    intended on AN-1204), but a direct read by id is denied without a grant, and so is
    anything that exposes their contents, such as document search (PLSV-827).
    """
    if cls is AccessClass.SHARED:
        return Expect.ALLOW if verb in (R, U) else Expect.DENY
    if cls is AccessClass.RESTRICTED:
        return Expect.ALLOW if verb is R else Expect.DENY
    if cls is AccessClass.PRIVATE:
        if verb is R and path is not None and path not in DIRECT_PATHS | CONTENT_PATHS:
            return Expect.ALLOW
        return Expect.DENY
    return Expect.DENY
