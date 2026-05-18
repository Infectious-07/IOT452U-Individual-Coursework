from __future__ import annotations

import re
from datetime import date

from .exceptions import ValidationError
from .identity import (
    DrivingEntitlement,
    DrivingRestriction,
    ResidencyStatus,
    TaxBand,
)

_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,98}[A-Za-z.]$")
_ID_PATTERN = re.compile(r"^[A-Z0-9\-]{4,32}$")
_NATIONALITY_PATTERN = re.compile(r"^[A-Z]{2}$")
_TAX_REF_PATTERN = re.compile(r"^[A-Z0-9]{6,16}$")


def validate_identity_id(identity_id: str) -> str:
    cleaned = (identity_id or "").strip().upper()
    if not _ID_PATTERN.fullmatch(cleaned):
        raise ValidationError("id", "must be 4 to 32 chars of A-Z, 0-9 or dash")
    return cleaned


def validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if len(cleaned) < 2:
        raise ValidationError("name", "must be at least two characters")
    if not _NAME_PATTERN.fullmatch(cleaned):
        raise ValidationError("name", "contains unsupported characters")
    return cleaned


def validate_dob(value: str | date) -> date:
    if isinstance(value, date):
        dob = value
    else:
        try:
            dob = date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError("dob", "expected ISO date YYYY-MM-DD") from exc
    if dob > date.today():
        raise ValidationError("dob", "cannot be in the future")
    return dob


def validate_nationality(value: str) -> str:
    cleaned = (value or "").strip().upper()
    if not _NATIONALITY_PATTERN.fullmatch(cleaned):
        raise ValidationError("nationality", "expected ISO 3166 alpha-2 code")
    return cleaned


def validate_address(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError("address", "cannot be empty")
    if len(cleaned) > 200:
        raise ValidationError("address", "must be 200 characters or fewer")
    return cleaned


def validate_tax_reference(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    cleaned = str(value).strip().upper()
    if not _TAX_REF_PATTERN.fullmatch(cleaned):
        raise ValidationError("tax_reference", "expected 6 to 16 alphanumerics")
    return cleaned


def validate_tax_band(value: str | None) -> TaxBand | None:
    if value is None or not str(value).strip():
        return None
    try:
        return TaxBand(str(value).strip().upper())
    except ValueError as exc:
        raise ValidationError("tax_band", "unknown tax band") from exc


def validate_residency_status(value: str | None) -> ResidencyStatus:
    if value is None or not str(value).strip():
        return ResidencyStatus.NONE
    try:
        return ResidencyStatus(str(value).strip().upper())
    except ValueError as exc:
        raise ValidationError("residency_status", "unknown residency status") from exc


def _validate_codes(field_name: str, value, enum_cls):
    if value is None or value == "":
        return frozenset()
    if isinstance(value, str):
        parts = [piece.strip().upper() for piece in value.split(",") if piece.strip()]
    else:
        parts = [str(piece).strip().upper() for piece in value if str(piece).strip()]
    result = set()
    for piece in parts:
        try:
            result.add(enum_cls(piece))
        except ValueError as exc:
            raise ValidationError(field_name, f"unknown code: {piece}") from exc
    return frozenset(result)


def validate_driving_entitlements(value) -> frozenset[DrivingEntitlement]:
    return _validate_codes("driving_entitlements", value, DrivingEntitlement)


def validate_driving_restrictions(value) -> frozenset[DrivingRestriction]:
    return _validate_codes("driving_restrictions", value, DrivingRestriction)
