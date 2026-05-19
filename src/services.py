from __future__ import annotations

import csv
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from database import AuditRepository, IdentityRepository
from models import (
    AuditAction,
    AuditEvent,
    AuthorisationError,
    DigitalID,
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    InvalidTransitionError,
    OrganisationRole,
    TaxBand,
    ValidationError,
    assert_allowed,
    require,
    utc_now,
    validate_dob,
    validate_driving_entitlements,
    validate_driving_restrictions,
    validate_identity_id,
    validate_name,
    validate_nationality,
    validate_postcode,
    validate_residency_status,
    validate_tax_band,
    validate_tax_reference,
)

# --- audit service ---


class AuditService:
    """Append-only audit log that records every lifecycle and verification event."""

    def __init__(
        self,
        events: AuditRepository,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._events = events
        self._clock = clock

    def record(
        self,
        actor: OrganisationRole,
        action: AuditAction,
        identity_id: str | None,
        payload: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            occurred_at=self._clock(),
            actor_role=actor.value,
            action=action,
            identity_id=identity_id,
            payload=dict(payload or {}),
        )
        self._events.append(event)
        return event

    def history_for(self, identity_id: str) -> list[AuditEvent]:
        return list(self._events.list_for_identity(identity_id))

    def events_between(
        self, start: datetime, end: datetime, identity_id: str | None = None
    ) -> list[AuditEvent]:
        return list(self._events.list_between(start, end, identity_id))


# --- identity service ---


@dataclass(frozen=True)
class NewIdentity:
    """Input payload for `IdentityService.create`.

    All fields arrive as untrusted strings or string-or-list pairs. The service
    validates each field before constructing a `DigitalID`.
    """

    identity_id: str
    name: str
    dob: str
    nationality: str
    postcode: str
    tax_reference: str | None = None
    tax_band: str | None = None
    driving_entitlements: str | list[str] = ""
    driving_restrictions: str | list[str] = ""
    right_to_work: bool = False
    residency_status: str | None = None


class IdentityService:
    """Manages the full lifecycle of Digital ID records with role-based authorisation."""

    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._identities = identities
        self._audit = audit
        self._clock = clock

    def create(self, actor: OrganisationRole, payload: NewIdentity) -> DigitalID:
        require(actor, "create")
        identity = DigitalID(
            id=validate_identity_id(payload.identity_id),
            name=validate_name(payload.name),
            dob=validate_dob(payload.dob),
            nationality=validate_nationality(payload.nationality),
            postcode=validate_postcode(payload.postcode),
            status=IdentityStatus.ACTIVE,
            tax_reference=validate_tax_reference(payload.tax_reference),
            tax_band=validate_tax_band(payload.tax_band),
            driving_entitlements=validate_driving_entitlements(payload.driving_entitlements),
            driving_restrictions=validate_driving_restrictions(payload.driving_restrictions),
            right_to_work=bool(payload.right_to_work),
            residency_status=validate_residency_status(payload.residency_status),
            created_at=self._clock(),
            updated_at=self._clock(),
        )
        self._identities.add(identity)
        self._audit.record(
            actor,
            AuditAction.CREATE,
            identity.id,
            {
                "name": identity.name,
                "dob": identity.dob.isoformat(),
                "nationality": identity.nationality,
            },
        )
        return identity

    def update_name(
        self,
        actor: OrganisationRole,
        identity_id: str,
        new_name: str,
    ) -> DigitalID:
        require(actor, "update")
        clean_name = validate_name(new_name)
        current = self._fetch_mutable(identity_id, "update")
        if current.name == clean_name:
            return current
        updated = current.with_name(clean_name, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {"field": "name", "from": current.name, "to": updated.name},
        )
        return updated

    def update_postcode(
        self,
        actor: OrganisationRole,
        identity_id: str,
        new_postcode: str,
    ) -> DigitalID:
        require(actor, "update")
        clean = validate_postcode(new_postcode)
        current = self._fetch_mutable(identity_id, "update")
        if current.postcode == clean:
            return current
        updated = current.with_postcode(clean, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {"field": "postcode"},
        )
        return updated

    def update_tax_details(
        self,
        actor: OrganisationRole,
        identity_id: str,
        reference: str | None,
        band: str | None,
    ) -> DigitalID:
        require(actor, "update")
        ref = validate_tax_reference(reference)
        band_value = validate_tax_band(band)
        current = self._fetch_mutable(identity_id, "update")
        if current.tax_reference == ref and current.tax_band == band_value:
            return current
        updated = current.with_tax_details(ref, band_value, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {"field": "tax", "band": band_value.value if band_value else None},
        )
        return updated

    def update_driving(
        self,
        actor: OrganisationRole,
        identity_id: str,
        entitlements: str | list[str],
        restrictions: str | list[str],
    ) -> DigitalID:
        require(actor, "update")
        ents = validate_driving_entitlements(entitlements)
        rests = validate_driving_restrictions(restrictions)
        current = self._fetch_mutable(identity_id, "update")
        if current.driving_entitlements == ents and current.driving_restrictions == rests:
            return current
        updated = current.with_driving(ents, rests, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {
                "field": "driving",
                "entitlements": sorted(item.value for item in ents),
                "restrictions": sorted(item.value for item in rests),
            },
        )
        return updated

    def update_eligibility(
        self,
        actor: OrganisationRole,
        identity_id: str,
        right_to_work: bool,
        residency: str | None,
    ) -> DigitalID:
        require(actor, "update")
        residency_value = validate_residency_status(residency)
        current = self._fetch_mutable(identity_id, "update")
        if (
            current.right_to_work == bool(right_to_work)
            and current.residency_status is residency_value
        ):
            return current
        updated = current.with_eligibility(
            bool(right_to_work), residency_value, self._clock()
        )
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {
                "field": "eligibility",
                "right_to_work": updated.right_to_work,
                "residency": updated.residency_status.value,
            },
        )
        return updated

    def suspend(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "suspend")
        return self._transition(actor, identity_id, IdentityStatus.SUSPENDED, AuditAction.SUSPEND)

    def revoke(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "revoke")
        return self._transition(actor, identity_id, IdentityStatus.REVOKED, AuditAction.REVOKE)

    def reactivate(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "reactivate")
        return self._transition(actor, identity_id, IdentityStatus.ACTIVE, AuditAction.REACTIVATE)

    def get(self, identity_id: str) -> DigitalID:
        return self._identities.get(validate_identity_id(identity_id))

    def list_all(self) -> list[DigitalID]:
        return list(self._identities.list_all())

    def _fetch_mutable(self, identity_id: str, action: str) -> DigitalID:
        clean_id = validate_identity_id(identity_id)
        current = self._identities.get(clean_id)
        if current.status is IdentityStatus.REVOKED:
            raise InvalidTransitionError(current.status.value, action)
        return current

    def _transition(
        self,
        actor: OrganisationRole,
        identity_id: str,
        target: IdentityStatus,
        action: AuditAction,
    ) -> DigitalID:
        clean_id = validate_identity_id(identity_id)
        current = self._identities.get(clean_id)
        assert_allowed(current.status, target)
        if current.status is target:
            return current
        updated = current.with_status(target, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            action,
            updated.id,
            {"from_status": current.status.value, "to_status": updated.status.value},
        )
        return updated


# --- verification service ---


@dataclass(frozen=True)
class EmployerResponse:
    """Verification response scoped to the employer's needs (validity + right to work)."""

    identity_id: str
    valid_now: bool
    right_to_work: bool


@dataclass(frozen=True)
class DvlaResponse:
    """Verification response scoped to driving licensing.

    `entitlements` and `restrictions` are populated only when the identity is
    currently active; the DVLA does not see them for suspended or revoked IDs.
    """

    identity_id: str
    exists: bool
    active_now: bool
    restricted_now: bool
    entitlements: frozenset[DrivingEntitlement] = field(default_factory=frozenset)
    restrictions: frozenset[DrivingRestriction] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TaxResponse:
    """Verification response scoped to a tax reporting period.

    `suspended_in_period` reflects an event-replay over the audit log between
    `period_start` and `period_end`. `tax_reference` and `tax_band` are
    populated only when the identity is currently active.
    """

    identity_id: str
    exists: bool
    active_now: bool
    suspended_in_period: bool
    period_start: date
    period_end: date
    tax_reference: str | None = None
    tax_band: TaxBand | None = None


class VerificationService:
    """Role-scoped identity verification that returns only the fields each consumer needs."""

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
        # Linear scan over the identity's audit history. Acceptable at the
        # expected scale of this coursework; a snapshot table would replace
        # this if call frequency grew.
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

    def _check_role(
        self,
        actor: OrganisationRole,
        expected: OrganisationRole,
        endpoint: str,
    ) -> None:
        if actor is not expected:
            raise AuthorisationError(actor.value, endpoint)
        require(actor, "verify")

    def _was_suspended_in_period(
        self,
        identity_id: str,
        period_start: date,
        period_end: date,
    ) -> bool:
        window_start = datetime.combine(period_start, time.min)
        window_end = datetime.combine(period_end, time.max)
        status_at_start = self._status_at(identity_id, window_start)
        in_period = self._audit.events_between(window_start, window_end, identity_id)
        return (
            status_at_start is IdentityStatus.SUSPENDED
            or any(event.action is AuditAction.SUSPEND for event in in_period)
        )

    def verify_for_tax(
        self,
        actor: OrganisationRole,
        identity_id: str,
        period_start: date,
        period_end: date,
    ) -> TaxResponse:
        self._check_role(actor, OrganisationRole.TAX, "verify_for_tax")
        if period_end < period_start:
            raise ValidationError("period", "end is before start")
        clean_id = validate_identity_id(identity_id)
        identity = self._fetch(clean_id)
        exists = identity is not None
        active_now = identity is not None and identity.status is IdentityStatus.ACTIVE
        suspended_in_period = (
            self._was_suspended_in_period(clean_id, period_start, period_end)
            if identity is not None
            else False
        )
        response = TaxResponse(
            identity_id=clean_id,
            exists=exists,
            active_now=active_now,
            suspended_in_period=suspended_in_period,
            period_start=period_start,
            period_end=period_end,
            tax_reference=identity.tax_reference if active_now else None,
            tax_band=identity.tax_band if active_now else None,
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
        self._check_role(actor, OrganisationRole.DVLA, "verify_for_dvla")
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
            entitlements=identity.driving_entitlements if active_now else frozenset(),
            restrictions=identity.driving_restrictions if active_now else frozenset(),
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
        self._check_role(actor, OrganisationRole.EMPLOYER, "verify_for_employer")
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


# --- export service ---


IDENTITY_COLUMNS = ("id", "name", "dob", "status", "created_at", "updated_at")
AUDIT_COLUMNS = ("occurred_at", "actor_role", "action", "identity_id", "payload")


class ExportService:
    """Writes identity and audit data to CSV files for the central authority."""

    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditRepository,
    ) -> None:
        self._identities = identities
        self._audit = audit

    def export_identities(self, actor: OrganisationRole, target: Path) -> int:
        require(actor, "export")
        target.parent.mkdir(parents=True, exist_ok=True)
        records = list(self._identities.list_all())
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(IDENTITY_COLUMNS)
            for identity in records:
                writer.writerow(
                    [
                        identity.id,
                        identity.name,
                        identity.dob.isoformat(),
                        identity.status.value,
                        identity.created_at.isoformat(),
                        identity.updated_at.isoformat(),
                    ]
                )
        return len(records)

    def export_audit(self, actor: OrganisationRole, target: Path) -> int:
        require(actor, "export")
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = list(self._audit.list_between(datetime.min, datetime.max))
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(AUDIT_COLUMNS)
            for event in rows:
                writer.writerow(
                    [
                        event.occurred_at.isoformat(),
                        event.actor_role,
                        event.action.value,
                        event.identity_id or "",
                        json.dumps(dict(event.payload), sort_keys=True),
                    ]
                )
        return len(rows)


# --- stats service ---


@dataclass(frozen=True)
class Snapshot:
    """System-wide statistics returned by `StatsService.snapshot`."""

    total: int
    by_status: Mapping[str, int]
    events_last_7_days: int


class StatsService:
    """Produces status distribution and activity snapshots for the dashboard."""

    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditRepository,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._identities = identities
        self._audit = audit
        self._clock = clock

    def snapshot(self, actor: OrganisationRole) -> Snapshot:
        require(actor, "stats")
        records = list(self._identities.list_all())
        by_status: dict[str, int] = {status.value: 0 for status in IdentityStatus}
        for identity in records:
            by_status[identity.status.value] += 1
        now = self._clock()
        recent = list(self._audit.list_between(now - timedelta(days=7), now))
        return Snapshot(
            total=len(records),
            by_status=by_status,
            events_last_7_days=len(recent),
        )
