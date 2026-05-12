from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..authorisation.roles import OrganisationRole, require
from ..domain.identity import IdentityStatus
from ..persistence.audit_repository import AuditRepository
from ..persistence.identity_repository import IdentityRepository


@dataclass(frozen=True)
class Snapshot:
    total: int
    by_status: dict[str, int]
    events_last_7_days: int


class StatsService:
    def __init__(
        self,
        identities: IdentityRepository,
        audit: AuditRepository,
        clock: Callable[[], datetime] = datetime.utcnow,
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
