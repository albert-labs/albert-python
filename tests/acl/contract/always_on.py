"""Actions every authenticated standard user may perform, whatever their role.

Agreed on SDK-216. A role with zero policies must still be allowed each of these; a
denial is a finding. ``NOT_ALWAYS_ON`` lists actions that must be denied without a
granting policy.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Probe:
    name: str
    method: str
    path: str
    params: dict | None = None


ALWAYS_ON: tuple[Probe, ...] = (
    Probe("own_profile", "GET", "/api/v3/login/validatejwt", {"includeUserDetails": "true"}),
    Probe("personal_view_order", "GET", "/api/v3/views/sequence", {"entity": "projects"}),
    Probe("parameters_read", "GET", "/api/v3/parameters", {"limit": 5}),
    Probe("data_columns_read", "GET", "/api/v3/datacolumns", {"limit": 5}),
    Probe("units_read", "GET", "/api/v3/units", {"limit": 5}),
    Probe("lists_read", "GET", "/api/v3/lists", {"limit": 5}),
    Probe("locations_read", "GET", "/api/v3/locations", {"limit": 5}),
    Probe("tags_read", "GET", "/api/v3/tags", {"limit": 5}),
    Probe("companies_read", "GET", "/api/v3/companies", {"limit": 5}),
    Probe("cas_read", "GET", "/api/v3/cas", {"limit": 5}),
    Probe("attributes_read", "GET", "/api/v3/attributes", {"limit": 5}),
    Probe("user_picker_search", "GET", "/api/v3/users/search", {"text": "a", "limit": 5}),
    Probe("team_picker_search", "GET", "/api/v3/teams/search", {"text": "a", "limit": 5}),
    Probe(
        "jurisdictions_languages",
        "GET",
        "/api/v3/attachments/jurisdictionslanguages",
        {"type": "language"},
    ),
)

NOT_ALWAYS_ON: tuple[Probe, ...] = (
    Probe("activities_audit", "GET", "/api/v3/activities", {"limit": 5}),
    Probe("roles_list", "GET", "/api/v3/acl/roles"),
)
