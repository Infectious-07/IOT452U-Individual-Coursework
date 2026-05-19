from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest

from database import AuditRepository, IdentityRepository, bootstrap, connect
from models import DigitalID, IdentityStatus, OrganisationRole, ResidencyStatus
from services import AuditService, IdentityService, NewIdentity, VerificationService


def _stepping_clock(start: datetime) -> Callable[[], datetime]:
    holder = {"now": start}

    def _tick() -> datetime:
        current = holder["now"]
        holder["now"] = current + timedelta(seconds=1)
        return current

    return _tick


def make_new_identity(
    identity_id: str = "ID-001",
    name: str = "Ada Lovelace",
    dob: str = "1990-05-01",
    nationality: str = "GB",
    postcode: str = "SW1A 2AA",
    **overrides,
) -> NewIdentity:
    base = {
        "identity_id": identity_id,
        "name": name,
        "dob": dob,
        "nationality": nationality,
        "postcode": postcode,
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
        postcode="SW1A 2AA",
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
    yield identity_service, verification, audit, identities, audit_repo
    connection.close()


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
