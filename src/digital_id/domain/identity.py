from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum


class IdentityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


# id and dob are set at creation and never change after that
@dataclass(frozen=True)
class DigitalID:
    id: str
    name: str
    dob: date
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime

    # returns a new instance with the updated name, leaving the original untouched
    def with_name(self, new_name: str, now: datetime) -> "DigitalID":
        return replace(self, name=new_name, updated_at=now)

    # returns a new instance with the updated status, leaving the original untouched
    def with_status(self, new_status: IdentityStatus, now: datetime) -> "DigitalID":
        return replace(self, status=new_status, updated_at=now)
