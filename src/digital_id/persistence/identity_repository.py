from __future__ import annotations

import sqlite3
from datetime import date, datetime

from ..domain.exceptions import DuplicateIdentityError, IdentityNotFoundError
from ..domain.identity import (
    DigitalID,
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)


def _split_codes(value: str | None, enum_cls):
    if not value:
        return frozenset()
    return frozenset(enum_cls(piece) for piece in value.split(",") if piece)


def _join_codes(codes) -> str:
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
