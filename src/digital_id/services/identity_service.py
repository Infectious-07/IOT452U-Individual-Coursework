from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..authorisation.roles import OrganisationRole, require
from ..domain.exceptions import InvalidTransitionError
from ..domain.identity import DigitalID, IdentityStatus
from ..domain.validators import validate_dob, validate_identity_id, validate_name
from ..persistence.identity_repository import IdentityRepository


class IdentityService:
    def __init__(
        self,
        identities: IdentityRepository,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._identities = identities
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
        return updated

    def suspend(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "suspend")
        return self._transition(identity_id, IdentityStatus.SUSPENDED)

    def revoke(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "revoke")
        return self._transition(identity_id, IdentityStatus.REVOKED)

    def reactivate(self, actor: OrganisationRole, identity_id: str) -> DigitalID:
        require(actor, "reactivate")
        return self._transition(identity_id, IdentityStatus.ACTIVE)

    def _transition(self, identity_id: str, target: IdentityStatus) -> DigitalID:
        clean_id = validate_identity_id(identity_id)
        current = self._identities.get(clean_id)
        # revoked is terminal; no transitions are allowed afterwards
        if current.status is IdentityStatus.REVOKED and target is not IdentityStatus.REVOKED:
            raise InvalidTransitionError(current.status.value, target.value)
        # repeated request with the same target is a no-op
        if current.status is target:
            return current
        updated = current.with_status(target, self._clock())
        self._identities.update(updated)
        return updated

    def get(self, identity_id: str) -> DigitalID:
        clean_id = validate_identity_id(identity_id)
        return self._identities.get(clean_id)
