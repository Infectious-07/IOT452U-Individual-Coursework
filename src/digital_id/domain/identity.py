from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum


class IdentityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class TaxBand(StrEnum):
    BASIC = "BASIC"
    HIGHER = "HIGHER"
    ADDITIONAL = "ADDITIONAL"
    EXEMPT = "EXEMPT"


class ResidencyStatus(StrEnum):
    CITIZEN = "CITIZEN"
    RESIDENT = "RESIDENT"
    TEMPORARY = "TEMPORARY"
    NONE = "NONE"


class DrivingEntitlement(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    C1 = "C1"
    D = "D"
    D1 = "D1"


class DrivingRestriction(StrEnum):
    GLASSES = "GLASSES"
    AUTOMATIC_ONLY = "AUTOMATIC_ONLY"
    DAYTIME_ONLY = "DAYTIME_ONLY"
    HEARING_AID = "HEARING_AID"


# id, dob and nationality are fixed at creation. Everything else can be amended
# by the central authority through the lifecycle service.
@dataclass(frozen=True)
class DigitalID:
    id: str
    name: str
    dob: date
    nationality: str
    address: str
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime
    tax_reference: str | None = None
    tax_band: TaxBand | None = None
    driving_entitlements: frozenset[DrivingEntitlement] = field(default_factory=frozenset)
    driving_restrictions: frozenset[DrivingRestriction] = field(default_factory=frozenset)
    right_to_work: bool = False
    residency_status: ResidencyStatus = ResidencyStatus.NONE

    def with_name(self, new_name: str, now: datetime) -> DigitalID:
        return replace(self, name=new_name, updated_at=now)

    def with_status(self, new_status: IdentityStatus, now: datetime) -> DigitalID:
        return replace(self, status=new_status, updated_at=now)

    def with_address(self, new_address: str, now: datetime) -> DigitalID:
        return replace(self, address=new_address, updated_at=now)

    def with_tax_details(
        self,
        reference: str | None,
        band: TaxBand | None,
        now: datetime,
    ) -> DigitalID:
        return replace(self, tax_reference=reference, tax_band=band, updated_at=now)

    def with_driving(
        self,
        entitlements: frozenset[DrivingEntitlement],
        restrictions: frozenset[DrivingRestriction],
        now: datetime,
    ) -> DigitalID:
        return replace(
            self,
            driving_entitlements=entitlements,
            driving_restrictions=restrictions,
            updated_at=now,
        )

    def with_eligibility(
        self,
        right_to_work: bool,
        residency: ResidencyStatus,
        now: datetime,
    ) -> DigitalID:
        return replace(
            self,
            right_to_work=right_to_work,
            residency_status=residency,
            updated_at=now,
        )
