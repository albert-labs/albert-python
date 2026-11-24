import sys
import warnings

from albert.client import Albert, AsyncAlbert
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.core.utils import find_stack_level

__all__ = ["Albert", "AsyncAlbert", "AlbertClientCredentials", "AlbertSSOClient"]

__version__ = "1.78.0"

if sys.version_info[:2] == (3, 10):
    warnings.warn(
        "Python 3.10 reached end of life in October 2026. The Albert Python SDK will "
        "stop supporting it in releases after 2027-02-28. Upgrade to Python 3.11 or "
        "later to keep receiving updates.",
        FutureWarning,
        stacklevel=find_stack_level(),
    )
