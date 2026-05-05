from datetime import datetime
from pathlib import Path
from typing import Callable

import pytest

from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.services.audit_service import AuditService
from digital_id.services.identity_service import IdentityService


# fixed clock starting at a known instant; each call advances by one second
def _stepping_clock(start: datetime) -> Callable[[], datetime]:
    holder = {"now": start}

    def _tick() -> datetime:
        current = holder["now"]
        holder["now"] = current.replace(microsecond=0)
        from datetime import timedelta
        holder["now"] = holder["now"] + timedelta(seconds=1)
        return current

    return _tick


@pytest.fixture
def clock() -> Callable[[], datetime]:
    return _stepping_clock(datetime(2026, 1, 1, 9, 0, 0))


@pytest.fixture
def identity_service(tmp_path: Path, clock: Callable[[], datetime]) -> IdentityService:
    connection = connect(tmp_path / "service.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit = AuditService(AuditRepository(connection), clock=clock)
    return IdentityService(identities, audit, clock=clock)


@pytest.fixture
def audit_service(tmp_path: Path, clock: Callable[[], datetime]) -> AuditService:
    connection = connect(tmp_path / "audit_service.sqlite")
    bootstrap(connection)
    return AuditService(AuditRepository(connection), clock=clock)


@pytest.fixture
def wired_services(tmp_path: Path, clock: Callable[[], datetime]):
    from digital_id.services.verification import VerificationService

    connection = connect(tmp_path / "wired.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit = AuditService(AuditRepository(connection), clock=clock)
    identity_service = IdentityService(identities, audit, clock=clock)
    verification = VerificationService(identities, audit, clock=clock)
    return identity_service, verification, audit
