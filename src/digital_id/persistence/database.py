from __future__ import annotations

import sqlite3
from pathlib import Path

IDENTITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS identities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT NOT NULL,
    status TEXT NOT NULL,
    nationality TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
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

# columns added in later versions of the identity table; the bootstrap step
# adds them to existing databases so older deployments keep working
_IDENTITY_LATER_COLUMNS = [
    ("nationality", "TEXT NOT NULL DEFAULT ''"),
    ("address", "TEXT NOT NULL DEFAULT ''"),
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
