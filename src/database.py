from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from models import (
    AuditAction,
    AuditEvent,
    DigitalID,
    DrivingEntitlement,
    DrivingRestriction,
    DuplicateIdentityError,
    IdentityNotFoundError,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)

# --- schema ---

IDENTITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS identities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT NOT NULL,
    status TEXT NOT NULL,
    nationality TEXT NOT NULL DEFAULT '',
    postcode TEXT NOT NULL DEFAULT '',
    tax_reference TEXT,
    tax_band TEXT,
    driving_entitlements TEXT NOT NULL DEFAULT '',
    driving_restrictions TEXT NOT NULL DEFAULT '',
    right_to_work INTEGER NOT NULL DEFAULT 0,
    residency_status TEXT NOT NULL DEFAULT 'NONE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    identity_id TEXT,
    payload TEXT NOT NULL
)
"""

AUDIT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_audit_identity ON audit_events(identity_id)"
)

# columns added in later versions; bootstrap adds them to existing databases
_IDENTITY_LATER_COLUMNS = [
    ("nationality", "TEXT NOT NULL DEFAULT ''"),
    ("postcode", "TEXT NOT NULL DEFAULT ''"),
    ("tax_reference", "TEXT"),
    ("tax_band", "TEXT"),
    ("driving_entitlements", "TEXT NOT NULL DEFAULT ''"),
    ("driving_restrictions", "TEXT NOT NULL DEFAULT ''"),
    ("right_to_work", "INTEGER NOT NULL DEFAULT 0"),
    ("residency_status", "TEXT NOT NULL DEFAULT 'NONE'"),
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def _existing_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    # PRAGMA does not support parameterised queries; table name is always a literal
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def bootstrap(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(IDENTITY_SCHEMA)
        connection.execute(AUDIT_SCHEMA)
        connection.execute(AUDIT_INDEX)
        present = _existing_columns(connection, "identities")
        for column, definition in _IDENTITY_LATER_COLUMNS:
            if column not in present:
                connection.execute(
                    f"ALTER TABLE identities ADD COLUMN {column} {definition}"
                )


# --- identity repository ---


def _split_codes(value: str | None, enum_cls: type) -> frozenset:
    if not value:
        return frozenset()
    return frozenset(enum_cls(piece) for piece in value.split(",") if piece)


def _join_codes(codes: frozenset) -> str:
    return ",".join(sorted(code.value for code in codes))


def _row_to_identity(row: sqlite3.Row) -> DigitalID:
    return DigitalID(
        id=row["id"],
        name=row["name"],
        dob=date.fromisoformat(row["dob"]),
        status=IdentityStatus(row["status"]),
        nationality=row["nationality"],
        postcode=row["postcode"],
        tax_reference=row["tax_reference"],
        tax_band=TaxBand(row["tax_band"]) if row["tax_band"] else None,
        driving_entitlements=_split_codes(row["driving_entitlements"], DrivingEntitlement),
        driving_restrictions=_split_codes(row["driving_restrictions"], DrivingRestriction),
        right_to_work=bool(row["right_to_work"]),
        residency_status=ResidencyStatus(row["residency_status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _identity_row(identity: DigitalID) -> tuple:
    return (
        identity.id,
        identity.name,
        identity.dob.isoformat(),
        identity.status.value,
        identity.nationality,
        identity.postcode,
        identity.tax_reference,
        identity.tax_band.value if identity.tax_band else None,
        _join_codes(identity.driving_entitlements),
        _join_codes(identity.driving_restrictions),
        1 if identity.right_to_work else 0,
        identity.residency_status.value,
        identity.created_at.isoformat(),
        identity.updated_at.isoformat(),
    )


_INSERT_SQL = (
    "INSERT INTO identities ("
    "id, name, dob, status, nationality, postcode, tax_reference, tax_band, "
    "driving_entitlements, driving_restrictions, right_to_work, residency_status, "
    "created_at, updated_at"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_UPDATE_SQL = (
    "UPDATE identities SET name = ?, status = ?, postcode = ?, tax_reference = ?, "
    "tax_band = ?, driving_entitlements = ?, driving_restrictions = ?, "
    "right_to_work = ?, residency_status = ?, updated_at = ? WHERE id = ?"
)


class IdentityRepository:
    """SQLite-backed store for Digital ID records."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def add(self, identity: DigitalID) -> None:
        try:
            with self._conn:
                self._conn.execute(_INSERT_SQL, _identity_row(identity))
        except sqlite3.IntegrityError as exc:
            raise DuplicateIdentityError(identity.id) from exc

    def get(self, identity_id: str) -> DigitalID:
        row = self._conn.execute(
            "SELECT * FROM identities WHERE id = ?", (identity_id,)
        ).fetchone()
        if row is None:
            raise IdentityNotFoundError(identity_id)
        return _row_to_identity(row)

    def exists(self, identity_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM identities WHERE id = ?", (identity_id,)
        ).fetchone()
        return row is not None

    def update(self, identity: DigitalID) -> None:
        with self._conn:
            cursor = self._conn.execute(
                _UPDATE_SQL,
                (
                    identity.name,
                    identity.status.value,
                    identity.postcode,
                    identity.tax_reference,
                    identity.tax_band.value if identity.tax_band else None,
                    _join_codes(identity.driving_entitlements),
                    _join_codes(identity.driving_restrictions),
                    1 if identity.right_to_work else 0,
                    identity.residency_status.value,
                    identity.updated_at.isoformat(),
                    identity.id,
                ),
            )
        if cursor.rowcount == 0:
            raise IdentityNotFoundError(identity.id)

    def list_all(self) -> list[DigitalID]:
        rows = self._conn.execute("SELECT * FROM identities ORDER BY id").fetchall()
        return [_row_to_identity(row) for row in rows]


# --- audit repository ---


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        actor_role=row["actor_role"],
        action=AuditAction(row["action"]),
        identity_id=row["identity_id"],
        payload=json.loads(row["payload"]),
    )


class AuditRepository:
    """Append-only SQLite store for audit events."""

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
