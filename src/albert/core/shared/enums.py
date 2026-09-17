from enum import Enum


class OrderBy(str, Enum):
    """Sort direction for list and search results.

    Attributes
    ----------
    DESCENDING : str
        Reverse chronological or reverse alphabetical order (Z→A, newest→oldest).
    ASCENDING : str
        Chronological or alphabetical order (A→Z, oldest→newest).
    """

    DESCENDING = "desc"
    ASCENDING = "asc"


class Status(str, Enum):
    """The status of a resource.

    Attributes
    ----------
    ACTIVE : str
        The resource is fully operational and visible in normal operations.
    INACTIVE : str
        The resource is hidden from normal operations and disabled from use.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class SecurityClass(str, Enum):
    """The security (access control) class of a resource.

    Attributes
    ----------
    SHARED : str
        Accessible to all members of the tenant.
    RESTRICTED : str
        Access is restricted to specific teams or users.
    CONFIDENTIAL : str
        Access is limited to designated users only.
    PRIVATE : str
        Visible only to the owner. Used by Projects.
    """

    SHARED = "shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"


class PaginationMode(str, Enum):
    """Internal pagination strategy used by the SDK.

    Attributes
    ----------
    OFFSET : str
        Offset-based pagination using a numeric skip value.
    KEY : str
        Cursor-based pagination using an opaque ``startKey`` / ``lastKey`` pair.
    """

    OFFSET = "offset"
    KEY = "key"
