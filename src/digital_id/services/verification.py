from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from ..authorisation.roles import OrganisationRole, require
from ..domain.exceptions import AuthorisationError
from ..domain.identity import IdentityStatus
from ..domain.validators import validate_identity_id
from ..persistence.identity_repository import IdentityRepository
from .audit_service import AuditService


# Each consumer role gets a tailored response shape so portals do not
# leak attributes that are not relevant to their domain.
@dataclass(frozen=True)
class ValidityResponse:
    identity_id: str
    valid_now: bool


@dataclass(frozen=True)
class LookupResponse:
    identity_id: str
    valid_now: bool
    name: str | None


@dataclass(frozen=True)
class DvlaResponse:
    identity_id: str
    exists: bool
    active_now: bool
    restricted_now: bool


@dataclass(frozen=True)
class TaxResponse:
    identity_id: str
    exists: bool
    active_now: bool
    suspended_in_period: bool
    period_start: date
    period_end: date


class VerificationService:
    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditService,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._identities = identities
        self._audit = audit
        self._clock = clock

    def _exists_and_status(self, identity_id: str) -> tuple[bool, IdentityStatus | None, str | None]:
        if not self._identities.exists(identity_id):
            return False, None, None
        identity = self._identities.get(identity_id)
        return True, identity.status, identity.name

    def _ensure_verify_role(self, actor: OrganisationRole) -> None:
        try:
            require(actor, "verify")
        except AuthorisationError:
            raise
