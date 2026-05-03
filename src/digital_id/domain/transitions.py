from __future__ import annotations

from .exceptions import InvalidTransitionError
from .identity import IdentityStatus

# allowed source -> target moves; everything else is rejected
_ALLOWED: dict[IdentityStatus, set[IdentityStatus]] = {
    IdentityStatus.ACTIVE: {IdentityStatus.SUSPENDED, IdentityStatus.REVOKED},
    IdentityStatus.SUSPENDED: {IdentityStatus.ACTIVE, IdentityStatus.REVOKED},
    IdentityStatus.REVOKED: set(),
}


def is_allowed(current: IdentityStatus, target: IdentityStatus) -> bool:
    # treating a same to same call as allowed makes the caller idempotent
    if current is target:
        return True
    return target in _ALLOWED[current]


def assert_allowed(current: IdentityStatus, target: IdentityStatus) -> None:
    if not is_allowed(current, target):
        raise InvalidTransitionError(current.value, target.value)
