from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..authorisation.roles import OrganisationRole, require
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
