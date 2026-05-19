from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from ..clock import utc_now
from ..domain.exceptions import AuthorisationError, ValidationError
from ..domain.identity import (
    AuditAction,
    DigitalID,
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    TaxBand,
)
from ..domain.roles import OrganisationRole, require
from ..domain.validators import validate_identity_id
from ..persistence.identity_repository import IdentityRepository
from .audit_service import AuditService


@dataclass(frozen=True)
class EmployerResponse:
    identity_id: str
    valid_now: bool
    right_to_work: bool


@dataclass(frozen=True)
class DvlaResponse:
    identity_id: str
    exists: bool
    active_now: bool
    restricted_now: bool
    entitlements: frozenset[DrivingEntitlement] = field(default_factory=frozenset)
    restrictions: frozenset[DrivingRestriction] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TaxResponse:
    identity_id: str
    exists: bool
    active_now: bool
    suspended_in_period: bool
    period_start: date
    period_end: date
    tax_reference: str | None = None
    tax_band: TaxBand | None = None


class VerificationService:
    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._identities = identities
        self._audit = audit
        self._clock = clock

    def _fetch(self, identity_id: str) -> DigitalID | None:
        if not self._identities.exists(identity_id):
            return None
        return self._identities.get(identity_id)

    def _status_at(self, identity_id: str, when: datetime) -> IdentityStatus | None:
        events = self._audit.events_between(datetime.min, when, identity_id)
        status: IdentityStatus | None = None
        for event in events:
            if event.action is AuditAction.CREATE:
                status = IdentityStatus.ACTIVE
            elif event.action is AuditAction.SUSPEND:
                status = IdentityStatus.SUSPENDED
            elif event.action is AuditAction.REACTIVATE:
                status = IdentityStatus.ACTIVE
            elif event.action is AuditAction.REVOKE:
                status = IdentityStatus.REVOKED
        return status

    def _record(
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
        require(actor, "verify")
        if period_end < period_start:
            raise ValidationError("period", "end is before start")
        clean_id = validate_identity_id(identity_id)
        identity = self._fetch(clean_id)
        exists = identity is not None
        active_now = identity is not None and identity.status is IdentityStatus.ACTIVE
        suspended_in_period = False
        if identity is not None:
            window_start = datetime.combine(period_start, time.min)
            window_end = datetime.combine(period_end, time.max)
            status_at_start = self._status_at(clean_id, window_start)
            in_period = self._audit.events_between(window_start, window_end, clean_id)
            suspended_in_period = (
                status_at_start is IdentityStatus.SUSPENDED
                or any(event.action is AuditAction.SUSPEND for event in in_period)
            )
        response = TaxResponse(
            identity_id=clean_id,
            exists=exists,
            active_now=active_now,
            suspended_in_period=suspended_in_period,
            period_start=period_start,
            period_end=period_end,
            tax_reference=identity.tax_reference if identity else None,
            tax_band=identity.tax_band if identity else None,
        )
        self._record(
            actor,
            clean_id,
            {
                "kind": "tax",
                "exists": exists,
                "active_now": active_now,
                "suspended_in_period": suspended_in_period,
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
        require(actor, "verify")
        clean_id = validate_identity_id(identity_id)
        identity = self._fetch(clean_id)
        exists = identity is not None
        active_now = identity is not None and identity.status is IdentityStatus.ACTIVE
        restricted_now = identity is not None and identity.status is IdentityStatus.SUSPENDED
        response = DvlaResponse(
            identity_id=clean_id,
            exists=exists,
            active_now=active_now,
            restricted_now=restricted_now,
            entitlements=identity.driving_entitlements if identity else frozenset(),
            restrictions=identity.driving_restrictions if identity else frozenset(),
        )
        self._record(
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

    def verify_for_employer(
        self,
        actor: OrganisationRole,
        identity_id: str,
    ) -> EmployerResponse:
        if actor is not OrganisationRole.EMPLOYER:
            raise AuthorisationError(actor.value, "verify_for_employer")
        require(actor, "verify")
        clean_id = validate_identity_id(identity_id)
        identity = self._fetch(clean_id)
        valid_now = identity is not None and identity.status is IdentityStatus.ACTIVE
        right_to_work = bool(identity.right_to_work) if valid_now else False
        response = EmployerResponse(
            identity_id=clean_id,
            valid_now=valid_now,
            right_to_work=right_to_work,
        )
        self._record(
            actor,
            clean_id,
            {"kind": "employer", "valid_now": valid_now, "right_to_work": right_to_work},
        )
        return response
