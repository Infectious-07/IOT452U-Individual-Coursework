from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from ..clock import utc_now
from ..domain.identity import IdentityStatus
from ..domain.roles import OrganisationRole, require
from ..persistence.audit_repository import AuditRepository
from ..persistence.identity_repository import IdentityRepository

IDENTITY_COLUMNS = ("id", "name", "dob", "status", "created_at", "updated_at")
AUDIT_COLUMNS = ("occurred_at", "actor_role", "action", "identity_id", "payload")


class ExportService:
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
