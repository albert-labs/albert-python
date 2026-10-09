"""Record-level contract: FGC level x child kind -> verbs, plus class semantics.

Sources: FGC level names, PLSV-780 §3, the class matrix in the ACL functional spec, and
Lenore's SDK-216 decisions (ProjectAllTask sees formulas and batch/property tasks;
ProjectPropertyTask sees only the lots its property tasks test; ProjectViewer is the
legacy technician; sharing needs a Full policy plus an owner-level FGC; project delete is
admin-only). Cells marked undecided are open product questions and skip with a reason.
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
_TASKS_ALL = (K.GENERAL_TASK, K.PROPERTY_TASK, K.BATCH_TASK)


def _all(kinds, verbs) -> dict[Kind, frozenset[Verb]]:
    return {k: frozenset(verbs) for k in kinds}


PROJECT_LEVELS: dict[str, LevelContract] = {
    "ProjectOwner": LevelContract(
        "ProjectOwner",
        {
            K.PROJECT: frozenset({R, U, S}),
            K.FORMULA: RCUD,
            **_all(_TASKS_ALL, RCUD),
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
            **_all(_TASKS_ALL, RCUD),
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
            **_all(_TASKS_ALL, RCU),
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
            K.PROPERTY_TASK: RCU,
            K.BATCH_TASK: RCU,
            K.LOT: RCU,
            K.TASK_CHILD: RCUD,
            K.REPORT: frozenset({R, C}),
        },
        undecided={
            K.PROPERTY_TASK: frozenset({Verb.DELETE}),
            K.BATCH_TASK: frozenset({Verb.DELETE}),
            K.GENERAL_TASK: frozenset({R, C, U, Verb.DELETE}),
            K.PROJECT_CHILD: frozenset({R}),
        },
    ),
    "ProjectPropertyTask": LevelContract(
        "ProjectPropertyTask",
        {
            K.PROJECT: RO,
            K.PROPERTY_TASK: RCU,
            K.LOT: RU,
            K.TASK_CHILD: RCUD,
            K.REPORT: frozenset({R, C}),
        },
        undecided={
            K.PROPERTY_TASK: frozenset({Verb.DELETE}),
            K.GENERAL_TASK: frozenset({R, C, U, Verb.DELETE}),
            K.PROJECT_CHILD: frozenset({R}),
        },
    ),
    "ProjectStrictViewer": LevelContract(
        "ProjectStrictViewer",
        {
            K.PROJECT: RO,
            K.FORMULA: RO,
            **_all(_TASKS_ALL, RO),
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

SHARE_REQUIRES_FULL_POLICY = {
    K.PROJECT: "ProjectsFullAccess",
    K.INVENTORY: "InventoryFullAccess",
}

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


def class_expect(cls: AccessClass, verb: Verb, path: ReadPath | None = None) -> Expect:
    """Expected outcome for a standard user with no ACL entry on the record.

    Functional spec matrix (standard user, implicit / explicit):
    Shared I-All; Restricted I-Read/List; Private I-List; Confidential none.
    """
    if cls is AccessClass.SHARED:
        return Expect.ALLOW if verb in (R, U) else Expect.DENY
    if cls is AccessClass.RESTRICTED:
        return Expect.ALLOW if verb is R else Expect.DENY
    if cls is AccessClass.PRIVATE:
        if verb is not R:
            return Expect.DENY
        if path is not None and path in DIRECT_PATHS:
            return Expect.DENY
        return Expect.UNDECIDED
    return Expect.DENY


PRIVATE_LIST_UNDECIDED = (
    "Private implicit List: functional spec says Standard users may list Private records; "
    "SDK docs say Private is visible only to ACL members"
)
