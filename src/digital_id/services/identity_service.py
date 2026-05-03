from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..authorisation.roles import OrganisationRole, require
from ..domain.audit import AuditAction
from ..domain.exceptions import InvalidTransitionError
from ..domain.identity import DigitalID, IdentityStatus
from ..domain.transitions import assert_allowed
from ..domain.validators import validate_dob, validate_identity_id, validate_name
from ..persistence.identity_repository import IdentityRepository
from .audit_service import AuditService


class IdentityService:
    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditService,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._identities = identities
        self._audit = audit
        self._clock = clock

    def create(
        self,
        actor: OrganisationRole,
        identity_id: str,
        name: str,
        dob: str,
    ) -> DigitalID:
        require(actor, "create")
        clean_id = validate_identity_id(identity_id)
        clean_name = validate_name(name)
        clean_dob = validate_dob(dob)
        now = self._clock()
        identity = DigitalID(
            id=clean_id,
            name=clean_name,
            dob=clean_dob,
            status=IdentityStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._identities.add(identity)
        self._audit.record(
            actor,
            AuditAction.CREATE,
            identity.id,
            {"name": identity.name, "dob": identity.dob.isoformat()},
        )
        return identity

    def update_name(
        self,
        actor: OrganisationRole,
        identity_id: str,
        new_name: str,
    ) -> DigitalID:
        require(actor, "update")
        clean_id = validate_identity_id(identity_id)
        clean_name = validate_name(new_name)
        current = self._identities.get(clean_id)
        # changes are not accepted on revoked identities; the record is final
        if current.status is IdentityStatus.REVOKED:
            raise InvalidTransitionError(current.status.value, "update")
        # idempotent: no change means no write
        if current.name == clean_name:
            return current
        updated = current.with_name(clean_name, self._clock())
        self._identities.update(updated)
        self._audit.record(
            actor,
            AuditAction.UPDATE,
            updated.id,
            {"from_name": current.name, "to_name": updated.name},
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
        # repeated request with the same target is a no-op and not audited
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

    def get(self, identity_id: str) -> DigitalID:
        clean_id = validate_identity_id(identity_id)
        return self._identities.get(clean_id)
