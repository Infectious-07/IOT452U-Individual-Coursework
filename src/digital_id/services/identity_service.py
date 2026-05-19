from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ..clock import utc_now
from ..domain.exceptions import InvalidTransitionError
from ..domain.identity import (
    AuditAction,
    DigitalID,
    IdentityStatus,
    assert_allowed,
)
from ..domain.roles import OrganisationRole, require
from ..domain.validators import (
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
from ..persistence.identity_repository import IdentityRepository
from .audit_service import AuditService


@dataclass(frozen=True)
class NewIdentity:
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


__all__ = [
    "IdentityService",
    "NewIdentity",
]
