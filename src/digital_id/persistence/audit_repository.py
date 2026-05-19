from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ..domain.identity import AuditAction, AuditEvent


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        actor_role=row["actor_role"],
        action=AuditAction(row["action"]),
        identity_id=row["identity_id"],
        payload=json.loads(row["payload"]),
    )


class AuditRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    # append is the only mutation; update and delete are never exposed
    def append(self, event: AuditEvent) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO audit_events (occurred_at, actor_role, action, identity_id, payload)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    event.occurred_at.isoformat(),
                    event.actor_role,
                    event.action.value,
                    event.identity_id,
                    json.dumps(dict(event.payload), sort_keys=True),
                ),
            )

    def list_for_identity(self, identity_id: str) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT * FROM audit_events WHERE identity_id = ? ORDER BY occurred_at, id",
            (identity_id,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def list_between(
        self, start: datetime, end: datetime, identity_id: str | None = None
    ) -> list[AuditEvent]:
        if identity_id is None:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE occurred_at BETWEEN ? AND ?"
                " ORDER BY occurred_at, id",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE identity_id = ?"
                " AND occurred_at BETWEEN ? AND ? ORDER BY occurred_at, id",
                (identity_id, start.isoformat(), end.isoformat()),
            ).fetchall()
        return [_row_to_event(row) for row in rows]
