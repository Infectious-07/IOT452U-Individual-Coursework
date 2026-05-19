from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from database import AuditRepository, IdentityRepository
from models import OrganisationRole, require

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
