from __future__ import annotations

from enum import StrEnum

from .exceptions import AuthorisationError


class OrganisationRole(StrEnum):
    CENTRAL_AUTHORITY = "CENTRAL_AUTHORITY"
    TAX = "TAX"
    DVLA = "DVLA"
    EMPLOYER = "EMPLOYER"


LIFECYCLE_ACTIONS = {"create", "update", "suspend", "revoke", "reactivate"}
VERIFY_ACTIONS = {"verify"}
ADMIN_ACTIONS = {"history", "export", "stats", "list"}

_ROLE_PERMISSIONS: dict[OrganisationRole, set[str]] = {
    OrganisationRole.CENTRAL_AUTHORITY: LIFECYCLE_ACTIONS | VERIFY_ACTIONS | ADMIN_ACTIONS,
    OrganisationRole.TAX: VERIFY_ACTIONS,
    OrganisationRole.DVLA: VERIFY_ACTIONS,
    OrganisationRole.EMPLOYER: VERIFY_ACTIONS,
}


def is_allowed(role: OrganisationRole, action: str) -> bool:
    return action in _ROLE_PERMISSIONS.get(role, set())


def require(role: OrganisationRole, action: str) -> None:
    if not is_allowed(role, action):
        raise AuthorisationError(role.value, action)
