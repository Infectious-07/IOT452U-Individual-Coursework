from pathlib import Path

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.services.audit_service import AuditService
from digital_id.services.export_service import ExportService
from digital_id.services.identity_service import IdentityService

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


@pytest.fixture
def export_setup(tmp_path: Path):
    connection = connect(tmp_path / "export.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit_repo = AuditRepository(connection)
    audit = AuditService(audit_repo)
    service = IdentityService(identities, audit)
    exporter = ExportService(identities, audit_repo)
    return service, exporter, tmp_path


def test_export_identities_writes_a_row_per_record(export_setup) -> None:
    service, exporter, base = export_setup
    service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    service.create(CENTRAL, "ID-002", "Alan Turing", "1980-01-02")
    target = base / "identities.csv"
    count = exporter.export_identities(CENTRAL, target)
    assert count == 2
    lines = target.read_text().splitlines()
    assert lines[0].split(",")[0] == "id"
    assert len(lines) == 3


def test_export_audit_includes_lifecycle_events(export_setup) -> None:
    service, exporter, base = export_setup
    service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    service.suspend(CENTRAL, "ID-001")
    target = base / "audit.csv"
    count = exporter.export_audit(CENTRAL, target)
    assert count == 2
    content = target.read_text()
    assert "CREATE" in content
    assert "SUSPEND" in content


def test_export_blocked_for_consumer_roles(export_setup) -> None:
    _, exporter, base = export_setup
    with pytest.raises(AuthorisationError):
        exporter.export_identities(OrganisationRole.BANK, base / "denied.csv")
