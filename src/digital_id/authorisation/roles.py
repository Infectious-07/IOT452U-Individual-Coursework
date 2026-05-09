from __future__ import annotations

from enum import StrEnum

from ..domain.exceptions import AuthorisationError


class OrganisationRole(StrEnum):
    CENTRAL_AUTHORITY = "CENTRAL_AUTHORITY"
    TAX = "TAX"
    DVLA = "DVLA"
    BANK = "BANK"
    EMPLOYER = "EMPLOYER"
    WELFARE = "WELFARE"
    LOCAL_AUTHORITY = "LOCAL_AUTHORITY"


# lifecycle actions belong to the central authority only
LIFECYCLE_ACTIONS = {"create", "update", "suspend", "revoke", "reactivate"}
# every role can verify, but each gets a tailored response shape
VERIFY_ACTIONS = {"verify"}
# central authority can also pull history, exports and stats
ADMIN_ACTIONS = {"history", "export", "stats", "list"}

_ROLE_PERMISSIONS: dict[OrganisationRole, set[str]] = {
    OrganisationRole.CENTRAL_AUTHORITY: LIFECYCLE_ACTIONS | VERIFY_ACTIONS | ADMIN_ACTIONS,
    OrganisationRole.TAX: VERIFY_ACTIONS,
    OrganisationRole.DVLA: VERIFY_ACTIONS,
    OrganisationRole.BANK: VERIFY_ACTIONS,
    OrganisationRole.EMPLOYER: VERIFY_ACTIONS,
    OrganisationRole.WELFARE: VERIFY_ACTIONS,
    OrganisationRole.LOCAL_AUTHORITY: VERIFY_ACTIONS,
}


def is_allowed(role: OrganisationRole, action: str) -> bool:
    return action in _ROLE_PERMISSIONS.get(role, set())


def require(role: OrganisationRole, action: str) -> None:
    if not is_allowed(role, action):
        raise AuthorisationError(role.value, action)
