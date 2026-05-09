from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from ..authorisation.roles import OrganisationRole, require
from ..domain.audit import AuditAction
from ..domain.exceptions import AuthorisationError, ValidationError
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
        require(actor, "verify")

    def _record_verify(
        self,
        actor: OrganisationRole,
        identity_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        self._audit.record(actor, AuditAction.VERIFY, identity_id, payload)

    def verify_for_tax(
        self,
        actor: OrganisationRole,
        identity_id: str,
        period_start: date,
        period_end: date,
    ) -> TaxResponse:
        if actor is not OrganisationRole.TAX:
            raise AuthorisationError(actor.value, "verify_for_tax")
        self._ensure_verify_role(actor)
        if period_end < period_start:
            raise ValidationError("period", "end is before start")
        clean_id = validate_identity_id(identity_id)
        exists, status, _ = self._exists_and_status(clean_id)
        active_now = status is IdentityStatus.ACTIVE
        suspended_in_period = False
        if exists:
            window_start = datetime.combine(period_start, time.min)
            window_end = datetime.combine(period_end, time.max)
            events = self._audit.events_between(window_start, window_end, clean_id)
            suspended_in_period = any(event.action is AuditAction.SUSPEND for event in events)
            # if the identity is currently suspended and the period overlaps the
            # current state, treat that as a suspension within the period too
            if status is IdentityStatus.SUSPENDED:
                suspended_in_period = True
        response = TaxResponse(
            identity_id=clean_id,
            exists=exists,
            active_now=active_now,
            suspended_in_period=suspended_in_period,
            period_start=period_start,
            period_end=period_end,
        )
        self._record_verify(
            actor,
            clean_id,
            {
                "kind": "tax",
                "exists": exists,
                "active_now": active_now,
                "suspended_in_period": suspended_in_period,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            },
        )
        return response

    def verify_for_dvla(
        self,
        actor: OrganisationRole,
        identity_id: str,
    ) -> DvlaResponse:
        if actor is not OrganisationRole.DVLA:
            raise AuthorisationError(actor.value, "verify_for_dvla")
        self._ensure_verify_role(actor)
        clean_id = validate_identity_id(identity_id)
        exists, status, _ = self._exists_and_status(clean_id)
        active_now = status is IdentityStatus.ACTIVE
        # a current suspension is the only signal DVLA gets for a restriction
        restricted_now = status is IdentityStatus.SUSPENDED
        response = DvlaResponse(
            identity_id=clean_id,
            exists=exists,
            active_now=active_now,
            restricted_now=restricted_now,
        )
        self._record_verify(
            actor,
            clean_id,
            {
                "kind": "dvla",
                "exists": exists,
                "active_now": active_now,
                "restricted_now": restricted_now,
            },
        )
        return response

    def verify_validity(
        self,
        actor: OrganisationRole,
        identity_id: str,
    ) -> ValidityResponse:
        if actor not in (OrganisationRole.BANK, OrganisationRole.EMPLOYER):
            raise AuthorisationError(actor.value, "verify_validity")
        self._ensure_verify_role(actor)
        clean_id = validate_identity_id(identity_id)
        exists, status, _ = self._exists_and_status(clean_id)
        valid_now = exists and status is IdentityStatus.ACTIVE
        response = ValidityResponse(identity_id=clean_id, valid_now=valid_now)
        self._record_verify(actor, clean_id, {"kind": "validity", "valid_now": valid_now})
        return response

    def verify_lookup(
        self,
        actor: OrganisationRole,
        identity_id: str,
    ) -> LookupResponse:
        if actor not in (OrganisationRole.WELFARE, OrganisationRole.LOCAL_AUTHORITY):
            raise AuthorisationError(actor.value, "verify_lookup")
        self._ensure_verify_role(actor)
        clean_id = validate_identity_id(identity_id)
        exists, status, name = self._exists_and_status(clean_id)
        valid_now = exists and status is IdentityStatus.ACTIVE
        # only the name is shared back; dob and audit history are withheld
        response = LookupResponse(
            identity_id=clean_id,
            valid_now=valid_now,
            name=name if valid_now else None,
        )
        self._record_verify(
            actor,
            clean_id,
            {"kind": "lookup", "valid_now": valid_now},
        )
        return response
