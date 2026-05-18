from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from digital_id.domain.identity import (
    DigitalID,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)
from tests.conftest import make_sample_identity


@pytest.fixture
def sample_identity() -> DigitalID:
    return make_sample_identity()


def test_identity_is_immutable(sample_identity: DigitalID) -> None:
    with pytest.raises(FrozenInstanceError):
        sample_identity.name = "Other"


def test_with_name_returns_new_instance(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    updated = sample_identity.with_name("Ada L.", later)
    assert updated.name == "Ada L."
    assert sample_identity.name == "Ada Lovelace"


def test_with_status_returns_new_instance(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    suspended = sample_identity.with_status(IdentityStatus.SUSPENDED, later)
    assert suspended.status is IdentityStatus.SUSPENDED
    assert sample_identity.status is IdentityStatus.ACTIVE


def test_with_tax_details(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    updated = sample_identity.with_tax_details("UTR12345678", TaxBand.HIGHER, later)
    assert updated.tax_reference == "UTR12345678"
    assert updated.tax_band is TaxBand.HIGHER


def test_status_values_are_stable() -> None:
    assert IdentityStatus.ACTIVE.value == "ACTIVE"
    assert IdentityStatus.SUSPENDED.value == "SUSPENDED"
    assert IdentityStatus.REVOKED.value == "REVOKED"


def test_default_residency_is_none() -> None:
    identity = make_sample_identity("ID-002")
    # the helper overrides residency to CITIZEN, so we build a fresh one here
    bare = identity.__class__(
        id="ID-003",
        name="Alan Turing",
        dob=identity.dob,
        nationality="GB",
        address="Bletchley Park",
        status=IdentityStatus.ACTIVE,
        created_at=identity.created_at,
        updated_at=identity.updated_at,
    )
    assert bare.residency_status is ResidencyStatus.NONE
    assert bare.right_to_work is False
    assert bare.driving_entitlements == frozenset()
