from __future__ import annotations

import re
from datetime import date

from .exceptions import ValidationError

# names are stored as plain text; trimmed copies are what the system records
_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,98}[A-Za-z.]$")
_ID_PATTERN = re.compile(r"^[A-Z0-9\-]{4,32}$")


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
