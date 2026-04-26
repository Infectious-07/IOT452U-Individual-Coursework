from datetime import date, datetime

import pytest

from digital_id.domain.identity import DigitalID, IdentityStatus


@pytest.fixture
def sample_identity() -> DigitalID:
    now = datetime(2026, 1, 1, 9, 0, 0)
    return DigitalID(
        id="ID-001",
        name="Ada Lovelace",
        dob=date(1990, 5, 1),
        status=IdentityStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_identity_is_immutable(sample_identity: DigitalID) -> None:
    with pytest.raises(Exception):
        sample_identity.name = "Other"


def test_with_name_returns_new_instance(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    updated = sample_identity.with_name("Ada L.", later)
    assert updated.name == "Ada L."
    assert updated.updated_at == later
    assert sample_identity.name == "Ada Lovelace"


def test_with_status_returns_new_instance(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    suspended = sample_identity.with_status(IdentityStatus.SUSPENDED, later)
    assert suspended.status is IdentityStatus.SUSPENDED
    assert suspended.updated_at == later
    assert sample_identity.status is IdentityStatus.ACTIVE


def test_status_values_are_stable() -> None:
    assert IdentityStatus.ACTIVE.value == "ACTIVE"
    assert IdentityStatus.SUSPENDED.value == "SUSPENDED"
    assert IdentityStatus.REVOKED.value == "REVOKED"
