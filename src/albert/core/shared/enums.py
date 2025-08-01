from enum import Enum


class OrderBy(str, Enum):
    DESCENDING = "desc"
    ASCENDING = "asc"


class Status(str, Enum):
    """The status of a resource"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class SecurityClass(str, Enum):
    """The security class of a resource"""

    SHARED = "shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"


class PaginationMode(str, Enum):
    OFFSET = "offset"
    KEY = "key"
