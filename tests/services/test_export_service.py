import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError
from digital_id.services.export_service import ExportService
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


@pytest.fixture
def setup(wired, tmp_path):
    identity_service, _, _, identities, audit_repo = wired
    exporter = ExportService(identities, audit_repo)
    return identity_service, exporter, tmp_path


def test_export_identities_writes_a_row_per_record(setup) -> None:
    identity_service, exporter, base = setup
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    target = base / "identities.csv"
    count = exporter.export_identities(CENTRAL, target)
    assert count == 2
    lines = target.read_text().splitlines()
    assert lines[0].split(",")[0] == "id"
    assert len(lines) == 3


def test_export_audit_includes_lifecycle_events(setup) -> None:
    identity_service, exporter, base = setup
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.suspend(CENTRAL, "ID-001")
    target = base / "audit.csv"
    count = exporter.export_audit(CENTRAL, target)
    assert count == 2
    content = target.read_text()
    assert "CREATE" in content
    assert "SUSPEND" in content


def test_export_blocked_for_consumer_roles(setup) -> None:
    _, exporter, base = setup
    with pytest.raises(AuthorisationError):
        exporter.export_identities(OrganisationRole.BANK, base / "denied.csv")
