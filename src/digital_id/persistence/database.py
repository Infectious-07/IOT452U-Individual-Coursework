from __future__ import annotations

import sqlite3
from pathlib import Path

# table for identity records; one row per id
IDENTITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS identities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# append only audit log; rows are never updated or deleted by the app
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


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def bootstrap(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(IDENTITY_SCHEMA)
        connection.execute(AUDIT_SCHEMA)
        connection.execute(AUDIT_INDEX)
