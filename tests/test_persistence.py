from datetime import datetime
from pathlib import Path

import pytest
from tests.conftest import make_sample_identity

from digital_id.domain.exceptions import DuplicateIdentityError, IdentityNotFoundError
from digital_id.domain.identity import (
    AuditAction,
    AuditEvent,
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import AUDIT_SCHEMA, bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository

# identity repository

@pytest.fixture
def identities(tmp_path: Path):
    connection = connect(tmp_path / "identities.sqlite")
    bootstrap(connection)
    yield IdentityRepository(connection)
    connection.close()


def test_identity_add_and_get_roundtrip(identities: IdentityRepository) -> None:
    identity = make_sample_identity()
    identities.add(identity)
    assert identities.get(identity.id) == identity


def test_identity_rejects_duplicates(identities: IdentityRepository) -> None:
    identities.add(make_sample_identity())
    with pytest.raises(DuplicateIdentityError):
        identities.add(make_sample_identity())


def test_identity_get_missing_raises(identities: IdentityRepository) -> None:
    with pytest.raises(IdentityNotFoundError):
        identities.get("MISSING")


def test_identity_update_writes_mutable_fields(identities: IdentityRepository) -> None:
    identity = make_sample_identity()
    identities.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    identities.update(identity.with_status(IdentityStatus.SUSPENDED, later))
    assert identities.get(identity.id).status is IdentityStatus.SUSPENDED


def test_identity_round_trips_extended_fields(identities: IdentityRepository) -> None:
    identity = make_sample_identity()
    identities.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    updated = (
        identity.with_tax_details("UTR12345", TaxBand.HIGHER, later)
        .with_driving(
            frozenset({DrivingEntitlement.B, DrivingEntitlement.C1}),
            frozenset({DrivingRestriction.GLASSES}),
            later,
        )
        .with_eligibility(True, ResidencyStatus.RESIDENT, later)
    )
    identities.update(updated)
    fetched = identities.get(identity.id)
    assert fetched.tax_band is TaxBand.HIGHER
    assert DrivingEntitlement.B in fetched.driving_entitlements
    assert DrivingRestriction.GLASSES in fetched.driving_restrictions
    assert fetched.right_to_work is True
    assert fetched.residency_status is ResidencyStatus.RESIDENT


def test_identity_list_returns_sorted(identities: IdentityRepository) -> None:
    identities.add(make_sample_identity("ID-002"))
    identities.add(make_sample_identity("ID-001"))
    assert [item.id for item in identities.list_all()] == ["ID-001", "ID-002"]


def test_bootstrap_is_idempotent_on_existing_database(tmp_path: Path) -> None:
    path = tmp_path / "twice.sqlite"
    first = connect(path)
    bootstrap(first)
    first.close()
    second = connect(path)
    bootstrap(second)
    repo = IdentityRepository(second)
    repo.add(make_sample_identity())
    assert repo.exists("ID-001")
    second.close()


# audit repository

@pytest.fixture
def audit(tmp_path: Path):
    connection = connect(tmp_path / "audit.sqlite")
    bootstrap(connection)
    yield AuditRepository(connection)
    connection.close()


def _event(when: datetime, action: AuditAction, identity_id: str = "ID-001") -> AuditEvent:
    return AuditEvent(
        occurred_at=when,
        actor_role="CENTRAL_AUTHORITY",
        action=action,
        identity_id=identity_id,
        payload={"note": action.value},
    )


def test_audit_append_persists(audit: AuditRepository) -> None:
    audit.append(_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE))
    fetched = list(audit.list_for_identity("ID-001"))
    assert len(fetched) == 1
    assert fetched[0].action is AuditAction.CREATE


def test_audit_list_for_identity_orders_by_time(audit: AuditRepository) -> None:
    audit.append(_event(datetime(2026, 1, 2, 10, 0), AuditAction.SUSPEND))
    audit.append(_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE))
    actions = [event.action for event in audit.list_for_identity("ID-001")]
    assert actions == [AuditAction.CREATE, AuditAction.SUSPEND]


def test_audit_list_between_filters_by_period(audit: AuditRepository) -> None:
    audit.append(_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE))
    audit.append(_event(datetime(2026, 6, 1, 10, 0), AuditAction.SUSPEND))
    audit.append(_event(datetime(2026, 12, 1, 10, 0), AuditAction.REACTIVATE))
    middle = list(
        audit.list_between(datetime(2026, 5, 1), datetime(2026, 7, 1), "ID-001")
    )
    assert len(middle) == 1
    assert middle[0].action is AuditAction.SUSPEND


def test_update_nonexistent_identity_raises(identities: IdentityRepository) -> None:
    sample = make_sample_identity("ID-MISSING")
    with pytest.raises(IdentityNotFoundError):
        identities.update(sample)


def test_bootstrap_migration_adds_columns_to_legacy_table(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite"
    conn = connect(path)
    conn.execute(
        "CREATE TABLE identities ("
        "id TEXT PRIMARY KEY, name TEXT NOT NULL, dob TEXT NOT NULL, "
        "status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.execute(AUDIT_SCHEMA)
    conn.commit()
    bootstrap(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(identities)")}
    assert "nationality" in columns
    assert "tax_band" in columns
    assert "driving_entitlements" in columns
    assert "right_to_work" in columns
    assert "residency_status" in columns
    conn.close()


def test_audit_list_between_without_id_returns_all(audit: AuditRepository) -> None:
    audit.append(_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE, "ID-A"))
    audit.append(_event(datetime(2026, 1, 2, 10, 0), AuditAction.CREATE, "ID-B"))
    events = list(audit.list_between(datetime(2026, 1, 1), datetime(2026, 1, 3)))
    assert {event.identity_id for event in events} == {"ID-A", "ID-B"}
