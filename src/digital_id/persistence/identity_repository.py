from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Iterable

from ..domain.exceptions import DuplicateIdentityError, IdentityNotFoundError
from ..domain.identity import DigitalID, IdentityStatus


def _row_to_identity(row: sqlite3.Row) -> DigitalID:
    return DigitalID(
        id=row["id"],
        name=row["name"],
        dob=date.fromisoformat(row["dob"]),
        status=IdentityStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class IdentityRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def add(self, identity: DigitalID) -> None:
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO identities (id, name, dob, status, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        identity.id,
                        identity.name,
                        identity.dob.isoformat(),
                        identity.status.value,
                        identity.created_at.isoformat(),
                        identity.updated_at.isoformat(),
                    ),
                )
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
                "UPDATE identities SET name = ?, status = ?, updated_at = ? WHERE id = ?",
                (
                    identity.name,
                    identity.status.value,
                    identity.updated_at.isoformat(),
                    identity.id,
                ),
            )
        if cursor.rowcount == 0:
            raise IdentityNotFoundError(identity.id)

    def list_all(self) -> Iterable[DigitalID]:
        rows = self._conn.execute("SELECT * FROM identities ORDER BY id").fetchall()
        return [_row_to_identity(row) for row in rows]
