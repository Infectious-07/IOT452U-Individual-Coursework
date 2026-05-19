from datetime import datetime
from pathlib import Path

import pytest
from tests.conftest import make_new_identity

from exports import ExportService
from models import (
    AuthorisationError,
    DuplicateIdentityError,
    IdentityStatus,
    InvalidTransitionError,
    OrganisationRole,
    ResidencyStatus,
    TaxBand,
    ValidationError,
)
from services import StatsService

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
CONSUMER = OrganisationRole.EMPLOYER


# identity service

def test_create_returns_active_identity(wired) -> None:
    identity_service, *_ = wired
    identity = identity_service.create(CENTRAL, make_new_identity())
    assert identity.id == "ID-001"
    assert identity.status is IdentityStatus.ACTIVE
    assert identity.nationality == "GB"


def test_create_rejects_non_central_actor(wired) -> None:
    identity_service, *_ = wired
    with pytest.raises(AuthorisationError):
        identity_service.create(CONSUMER, make_new_identity())


def test_create_rejects_bad_input(wired) -> None:
    identity_service, *_ = wired
    with pytest.raises(ValidationError):
        identity_service.create(CENTRAL, make_new_identity(identity_id="AB"))


def test_create_rejects_duplicates(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    with pytest.raises(DuplicateIdentityError):
        identity_service.create(CENTRAL, make_new_identity())


def test_update_name_writes_new_value(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_name(CENTRAL, "ID-001", "Ada L.")
    assert updated.name == "Ada L."


def test_update_postcode(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_postcode(CENTRAL, "ID-001", "MK3 6EB")
    assert updated.postcode == "MK3 6EB"


def test_update_tax_details(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_tax_details(CENTRAL, "ID-001", "utr12345", "higher")
    assert updated.tax_reference == "UTR12345"
    assert updated.tax_band is TaxBand.HIGHER


def test_update_driving_set(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_driving(CENTRAL, "ID-001", "B,C1", "GLASSES")
    assert "B" in {entitlement.value for entitlement in updated.driving_entitlements}


def test_update_eligibility(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_eligibility(CENTRAL, "ID-001", True, "RESIDENT")
    assert updated.right_to_work is True
    assert updated.residency_status is ResidencyStatus.RESIDENT


def test_update_name_blocked_on_revoked(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.update_name(CENTRAL, "ID-001", "Ada L.")


def test_suspend_and_reactivate(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    suspended = identity_service.suspend(CENTRAL, "ID-001")
    reactivated = identity_service.reactivate(CENTRAL, "ID-001")
    assert suspended.status is IdentityStatus.SUSPENDED
    assert reactivated.status is IdentityStatus.ACTIVE


def test_revoked_is_terminal(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.reactivate(CENTRAL, "ID-001")


def test_update_name_noop_when_unchanged(wired) -> None:
    identity_service, *_ = wired
    original = identity_service.create(CENTRAL, make_new_identity())
    result = identity_service.update_name(CENTRAL, "ID-001", "Ada Lovelace")
    assert result.updated_at == original.updated_at


def test_update_postcode_noop_when_unchanged(wired) -> None:
    identity_service, *_ = wired
    original = identity_service.create(CENTRAL, make_new_identity())
    result = identity_service.update_postcode(CENTRAL, "ID-001", "SW1A 2AA")
    assert result.updated_at == original.updated_at


def test_update_tax_noop_when_unchanged(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(tax_reference="UTR12345", tax_band="HIGHER"))
    original = identity_service.get("ID-001")
    result = identity_service.update_tax_details(CENTRAL, "ID-001", "UTR12345", "HIGHER")
    assert result.updated_at == original.updated_at


def test_update_driving_noop_when_unchanged(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(driving_entitlements="B"))
    original = identity_service.get("ID-001")
    result = identity_service.update_driving(CENTRAL, "ID-001", "B", "")
    assert result.updated_at == original.updated_at


def test_update_eligibility_noop_when_unchanged(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(right_to_work=True, residency_status="CITIZEN"))
    original = identity_service.get("ID-001")
    result = identity_service.update_eligibility(CENTRAL, "ID-001", True, "CITIZEN")
    assert result.updated_at == original.updated_at


def test_transition_to_same_status_is_idempotent(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.suspend(CENTRAL, "ID-001")
    result = identity_service.suspend(CENTRAL, "ID-001")
    assert result.status is IdentityStatus.SUSPENDED


def test_list_all(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    listing = identity_service.list_all()
    assert {item.id for item in listing} == {"ID-001", "ID-002"}


# export and stats

@pytest.fixture
def admin_setup(wired, tmp_path: Path):
    identity_service, _, _, identities, audit_repo = wired
    exporter = ExportService(identities, audit_repo)
    stats = StatsService(
        identities, audit_repo, clock=lambda: datetime(2026, 5, 19, 12, 0, 0)
    )
    return identity_service, exporter, stats, tmp_path


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
