from datetime import datetime
from pathlib import Path

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError
from digital_id.services.export_service import ExportService
from digital_id.services.stats_service import StatsService
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


@pytest.fixture
def admin_setup(wired, tmp_path: Path):
    identity_service, _, _, identities, audit_repo = wired
    exporter = ExportService(identities, audit_repo)
    stats = StatsService(
        identities, audit_repo, clock=lambda: datetime(2026, 5, 19, 12, 0, 0)
    )
    return identity_service, exporter, stats, tmp_path


# export

def test_export_identities_writes_a_row_per_record(admin_setup) -> None:
    identity_service, exporter, _, base = admin_setup
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    target = base / "identities.csv"
    assert exporter.export_identities(CENTRAL, target) == 2
    lines = target.read_text().splitlines()
    assert lines[0].split(",")[0] == "id"
    assert len(lines) == 3


def test_export_audit_includes_lifecycle_events(admin_setup) -> None:
    identity_service, exporter, _, base = admin_setup
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.suspend(CENTRAL, "ID-001")
    target = base / "audit.csv"
    assert exporter.export_audit(CENTRAL, target) == 2
    content = target.read_text()
    assert "CREATE" in content
    assert "SUSPEND" in content


def test_export_blocked_for_consumer_roles(admin_setup) -> None:
    _, exporter, _, base = admin_setup
    with pytest.raises(AuthorisationError):
        exporter.export_identities(OrganisationRole.EMPLOYER, base / "denied.csv")


# stats

def test_snapshot_counts_status_distribution(admin_setup) -> None:
    identity_service, _, stats, _ = admin_setup
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    identity_service.suspend(CENTRAL, "ID-002")
    snapshot = stats.snapshot(CENTRAL)
    assert snapshot.total == 2
    assert snapshot.by_status == {"ACTIVE": 1, "SUSPENDED": 1, "REVOKED": 0}


def test_snapshot_blocked_for_consumer_roles(admin_setup) -> None:
    _, _, stats, _ = admin_setup
    with pytest.raises(AuthorisationError):
        stats.snapshot(OrganisationRole.TAX)


def test_snapshot_reports_recent_event_count_as_integer(admin_setup) -> None:
    identity_service, _, stats, _ = admin_setup
    identity_service.create(CENTRAL, make_new_identity())
    snapshot = stats.snapshot(CENTRAL)
    assert isinstance(snapshot.events_last_7_days, int)
    assert snapshot.events_last_7_days >= 0
