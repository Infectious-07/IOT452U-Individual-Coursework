from datetime import date, datetime
from pathlib import Path

import pytest

from digital_id.domain.exceptions import DuplicateIdentityError, IdentityNotFoundError
from digital_id.domain.identity import DigitalID, IdentityStatus
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository


@pytest.fixture
def repo(tmp_path: Path) -> IdentityRepository:
    connection = connect(tmp_path / "test.sqlite")
    bootstrap(connection)
    return IdentityRepository(connection)


def make_identity(identity_id: str = "ID-001") -> DigitalID:
    now = datetime(2026, 1, 1, 9, 0, 0)
    return DigitalID(
        id=identity_id,
        name="Ada Lovelace",
        dob=date(1990, 5, 1),
        status=IdentityStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_add_and_get_roundtrip(repo: IdentityRepository) -> None:
    identity = make_identity()
    repo.add(identity)
    fetched = repo.get(identity.id)
    assert fetched == identity


def test_add_rejects_duplicates(repo: IdentityRepository) -> None:
    repo.add(make_identity())
    with pytest.raises(DuplicateIdentityError):
        repo.add(make_identity())


def test_get_missing_raises(repo: IdentityRepository) -> None:
    with pytest.raises(IdentityNotFoundError):
        repo.get("MISSING")


def test_exists_reflects_presence(repo: IdentityRepository) -> None:
    assert not repo.exists("ID-001")
    repo.add(make_identity())
    assert repo.exists("ID-001")


def test_update_writes_mutable_fields(repo: IdentityRepository) -> None:
    identity = make_identity()
    repo.add(identity)
    later = datetime(2026, 2, 1, 9, 0, 0)
    updated = identity.with_status(IdentityStatus.SUSPENDED, later)
    repo.update(updated)
    fetched = repo.get(identity.id)
    assert fetched.status is IdentityStatus.SUSPENDED
    assert fetched.updated_at == later


def test_update_missing_raises(repo: IdentityRepository) -> None:
    with pytest.raises(IdentityNotFoundError):
        repo.update(make_identity("GHOST-1"))


def test_list_all_returns_sorted(repo: IdentityRepository) -> None:
    repo.add(make_identity("ID-002"))
    repo.add(make_identity("ID-001"))
    ids = [identity.id for identity in repo.list_all()]
    assert ids == ["ID-001", "ID-002"]
