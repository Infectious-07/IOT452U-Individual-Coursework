from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.identity import DigitalID, IdentityStatus, ResidencyStatus
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.services.audit_service import AuditService
from digital_id.services.identity_service import IdentityService, NewIdentity
from digital_id.services.verification import VerificationService


def _stepping_clock(start: datetime) -> Callable[[], datetime]:
    holder = {"now": start}

    def _tick() -> datetime:
        current = holder["now"]
        holder["now"] = current + timedelta(seconds=1)
        return current

    return _tick


# a shared default payload that every service test can reuse without ceremony
def make_new_identity(
    identity_id: str = "ID-001",
    name: str = "Ada Lovelace",
    dob: str = "1990-05-01",
    nationality: str = "GB",
    address: str = "10 Downing Street, London",
    **overrides,
) -> NewIdentity:
    base = {
        "identity_id": identity_id,
        "name": name,
        "dob": dob,
        "nationality": nationality,
        "address": address,
    }
    base.update(overrides)
    return NewIdentity(**base)


def make_sample_identity(identity_id: str = "ID-001") -> DigitalID:
    now = datetime(2026, 1, 1, 9, 0, 0)
    return DigitalID(
        id=identity_id,
        name="Ada Lovelace",
        dob=datetime(1990, 5, 1).date(),
        nationality="GB",
        address="10 Downing Street, London",
        status=IdentityStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        residency_status=ResidencyStatus.CITIZEN,
    )


@pytest.fixture
def clock() -> Callable[[], datetime]:
    return _stepping_clock(datetime(2026, 1, 1, 9, 0, 0))


@pytest.fixture
def wired(tmp_path: Path, clock):
    connection = connect(tmp_path / "wired.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit_repo = AuditRepository(connection)
    audit = AuditService(audit_repo, clock=clock)
    identity_service = IdentityService(identities, audit, clock=clock)
    verification = VerificationService(identities, audit, clock=clock)
    return identity_service, verification, audit, identities, audit_repo


@pytest.fixture
def captured_writer():
    buffer = StringIO()

    def writer(message: str) -> None:
        buffer.write(message + "\n")

    return buffer, writer


__all__ = [
    "OrganisationRole",
    "make_new_identity",
    "make_sample_identity",
]
