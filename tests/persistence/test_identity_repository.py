from datetime import datetime
from pathlib import Path

import pytest

from digital_id.domain.exceptions import DuplicateIdentityError, IdentityNotFoundError
from digital_id.domain.identity import (
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from tests.conftest import make_sample_identity


@pytest.fixture
def repo(tmp_path: Path) -> IdentityRepository:
    connection = connect(tmp_path / "test.sqlite")
    bootstrap(connection)
    return IdentityRepository(connection)


def test_add_and_get_roundtrip(repo: IdentityRepository) -> None:
    identity = make_sample_identity()
    repo.add(identity)
    assert repo.get(identity.id) == identity


def test_add_rejects_duplicates(repo: IdentityRepository) -> None:
    repo.add(make_sample_identity())
    with pytest.raises(DuplicateIdentityError):
        repo.add(make_sample_identity())


def test_get_missing_raises(repo: IdentityRepository) -> None:
    with pytest.raises(IdentityNotFoundError):
        repo.get("MISSING")


def test_update_writes_mutable_fields(repo: IdentityRepository) -> None:
    identity = make_sample_identity()
    repo.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    updated = identity.with_status(IdentityStatus.SUSPENDED, later)
    repo.update(updated)
    assert repo.get(identity.id).status is IdentityStatus.SUSPENDED


def test_round_trips_driving_and_tax(repo: IdentityRepository) -> None:
    identity = make_sample_identity()
    repo.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    with_tax = identity.with_tax_details("UTR12345", TaxBand.HIGHER, later)
    with_driving = with_tax.with_driving(
        frozenset({DrivingEntitlement.B, DrivingEntitlement.C1}),
        frozenset({DrivingRestriction.GLASSES}),
        later,
    )
    repo.update(with_driving)
    fetched = repo.get(identity.id)
    assert fetched.tax_band is TaxBand.HIGHER
    assert DrivingEntitlement.B in fetched.driving_entitlements
    assert DrivingRestriction.GLASSES in fetched.driving_restrictions


def test_round_trips_eligibility(repo: IdentityRepository) -> None:
    identity = make_sample_identity()
    repo.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    updated = identity.with_eligibility(True, ResidencyStatus.RESIDENT, later)
    repo.update(updated)
    fetched = repo.get(identity.id)
    assert fetched.right_to_work is True
    assert fetched.residency_status is ResidencyStatus.RESIDENT


def test_list_all_returns_sorted(repo: IdentityRepository) -> None:
    repo.add(make_sample_identity("ID-002"))
    repo.add(make_sample_identity("ID-001"))
    ids = [identity.id for identity in repo.list_all()]
    assert ids == ["ID-001", "ID-002"]


def test_bootstrap_is_idempotent_on_existing_db(tmp_path: Path) -> None:
    path = tmp_path / "twice.sqlite"
    first = connect(path)
    bootstrap(first)
    first.close()
    second = connect(path)
    bootstrap(second)
    repo = IdentityRepository(second)
    repo.add(make_sample_identity())
    assert repo.exists("ID-001")
