from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta

import pytest

from digital_id.domain.exceptions import (
    AuthorisationError,
    DigitalIdError,
    DuplicateIdentityError,
    IdentityNotFoundError,
    InvalidTransitionError,
    ValidationError,
)
from digital_id.domain.identity import (
    DigitalID,
    DrivingEntitlement,
    DrivingRestriction,
    IdentityStatus,
    ResidencyStatus,
    TaxBand,
)
from digital_id.domain.transitions import assert_allowed, is_allowed
from digital_id.domain.validators import (
    validate_dob,
    validate_driving_entitlements,
    validate_driving_restrictions,
    validate_identity_id,
    validate_name,
    validate_nationality,
    validate_postcode,
    validate_residency_status,
    validate_tax_band,
    validate_tax_reference,
)
from tests.conftest import make_sample_identity

# entity

@pytest.fixture
def sample_identity() -> DigitalID:
    return make_sample_identity()


def test_identity_is_immutable(sample_identity: DigitalID) -> None:
    with pytest.raises(FrozenInstanceError):
        sample_identity.name = "Other"


def test_mutators_return_new_instances(sample_identity: DigitalID) -> None:
    later = datetime(2026, 1, 2, 9, 0, 0)
    updated = sample_identity.with_name("Ada L.", later)
    assert updated.name == "Ada L."
    assert sample_identity.name == "Ada Lovelace"
    suspended = sample_identity.with_status(IdentityStatus.SUSPENDED, later)
    assert suspended.status is IdentityStatus.SUSPENDED
    with_tax = sample_identity.with_tax_details("UTR12345678", TaxBand.HIGHER, later)
    assert with_tax.tax_band is TaxBand.HIGHER


def test_status_values_are_stable() -> None:
    assert {status.value for status in IdentityStatus} == {"ACTIVE", "SUSPENDED", "REVOKED"}


# transitions

@pytest.mark.parametrize(
    "current,target,expected",
    [
        (IdentityStatus.ACTIVE, IdentityStatus.SUSPENDED, True),
        (IdentityStatus.ACTIVE, IdentityStatus.REVOKED, True),
        (IdentityStatus.SUSPENDED, IdentityStatus.ACTIVE, True),
        (IdentityStatus.SUSPENDED, IdentityStatus.REVOKED, True),
        (IdentityStatus.ACTIVE, IdentityStatus.ACTIVE, True),
        (IdentityStatus.REVOKED, IdentityStatus.ACTIVE, False),
        (IdentityStatus.REVOKED, IdentityStatus.SUSPENDED, False),
        (IdentityStatus.REVOKED, IdentityStatus.REVOKED, True),
    ],
)
def test_transition_matrix(current, target, expected) -> None:
    assert is_allowed(current, target) is expected


def test_assert_allowed_raises_on_forbidden() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_allowed(IdentityStatus.REVOKED, IdentityStatus.ACTIVE)


# exceptions

@pytest.mark.parametrize(
    "exc",
    [
        IdentityNotFoundError("ID-001"),
        DuplicateIdentityError("ID-001"),
        InvalidTransitionError("ACTIVE", "REVOKED"),
        ValidationError("name", "empty"),
        AuthorisationError("BANK", "create"),
    ],
)
def test_exceptions_inherit_from_base(exc) -> None:
    assert isinstance(exc, DigitalIdError)


def test_authorisation_error_carries_context() -> None:
    err = AuthorisationError("BANK", "create")
    assert err.role == "BANK"
    assert err.action == "create"


def test_invalid_transition_message_includes_both_states() -> None:
    err = InvalidTransitionError("ACTIVE", "REVOKED")
    assert "ACTIVE" in str(err)
    assert "REVOKED" in str(err)


# validators

def test_identity_id_normalises_and_validates() -> None:
    assert validate_identity_id("id-001") == "ID-001"
    with pytest.raises(ValidationError):
        validate_identity_id("ab")
    with pytest.raises(ValidationError):
        validate_identity_id("ID 001")


def test_name_validates() -> None:
    assert validate_name("  Ada Lovelace  ") == "Ada Lovelace"
    with pytest.raises(ValidationError):
        validate_name("")
    with pytest.raises(ValidationError):
        validate_name("Ada 9")


def test_dob_validates() -> None:
    assert validate_dob("1990-05-01") == date(1990, 5, 1)
    future = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        validate_dob(future)
    with pytest.raises(ValidationError):
        validate_dob("not-a-date")


def test_nationality_validates() -> None:
    assert validate_nationality("gb") == "GB"
    with pytest.raises(ValidationError):
        validate_nationality("GBR")


def test_postcode_validates() -> None:
    assert validate_postcode("sw1a 2aa") == "SW1A 2AA"
    assert validate_postcode("M1 1AE") == "M1 1AE"
    assert validate_postcode("EC2R8AH") == "EC2R8AH"
    with pytest.raises(ValidationError):
        validate_postcode("   ")
    with pytest.raises(ValidationError):
        validate_postcode("INVALID")


def test_tax_reference_validates() -> None:
    assert validate_tax_reference(None) is None
    assert validate_tax_reference("utr12345") == "UTR12345"
    with pytest.raises(ValidationError):
        validate_tax_reference("AB12")


def test_tax_band_validates() -> None:
    assert validate_tax_band(None) is None
    assert validate_tax_band("higher") is TaxBand.HIGHER
    with pytest.raises(ValidationError):
        validate_tax_band("ultra")


def test_residency_validates() -> None:
    assert validate_residency_status(None) is ResidencyStatus.TEMPORARY
    assert validate_residency_status("citizen") is ResidencyStatus.CITIZEN
    with pytest.raises(ValidationError):
        validate_residency_status("alien")


def test_driving_entitlements_validates() -> None:
    assert validate_driving_entitlements("B, C1") == frozenset(
        {DrivingEntitlement.B, DrivingEntitlement.C1}
    )
    assert validate_driving_entitlements(["A", "B"]) == frozenset(
        {DrivingEntitlement.A, DrivingEntitlement.B}
    )
    with pytest.raises(ValidationError):
        validate_driving_entitlements("Z")


def test_driving_restrictions_validates() -> None:
    assert validate_driving_restrictions("") == frozenset()
    assert validate_driving_restrictions("glasses,automatic_only") == frozenset(
        {DrivingRestriction.GLASSES, DrivingRestriction.AUTOMATIC_ONLY}
    )
