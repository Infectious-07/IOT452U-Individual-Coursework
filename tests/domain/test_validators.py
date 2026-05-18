from datetime import date, timedelta

import pytest

from digital_id.domain.exceptions import ValidationError
from digital_id.domain.identity import (
    DrivingEntitlement,
    DrivingRestriction,
    ResidencyStatus,
    TaxBand,
)
from digital_id.domain.validators import (
    validate_address,
    validate_dob,
    validate_driving_entitlements,
    validate_driving_restrictions,
    validate_identity_id,
    validate_name,
    validate_nationality,
    validate_residency_status,
    validate_tax_band,
    validate_tax_reference,
)


def test_identity_id_normalises_to_upper() -> None:
    assert validate_identity_id("id-001") == "ID-001"


def test_identity_id_rejects_short_value() -> None:
    with pytest.raises(ValidationError):
        validate_identity_id("ab")


def test_name_trims_and_accepts() -> None:
    assert validate_name("  Ada Lovelace  ") == "Ada Lovelace"


def test_name_rejects_digits() -> None:
    with pytest.raises(ValidationError):
        validate_name("Ada 9")


def test_dob_accepts_iso() -> None:
    assert validate_dob("1990-05-01") == date(1990, 5, 1)


def test_dob_rejects_future() -> None:
    future = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        validate_dob(future)


def test_nationality_uppercases() -> None:
    assert validate_nationality("gb") == "GB"


def test_nationality_rejects_long_value() -> None:
    with pytest.raises(ValidationError):
        validate_nationality("GBR")


def test_address_strips() -> None:
    assert validate_address("  10 Downing Street  ") == "10 Downing Street"


def test_address_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        validate_address("   ")


def test_address_rejects_overlong() -> None:
    with pytest.raises(ValidationError):
        validate_address("x" * 201)


def test_tax_reference_optional() -> None:
    assert validate_tax_reference(None) is None
    assert validate_tax_reference(" ") is None


def test_tax_reference_uppercases_and_validates() -> None:
    assert validate_tax_reference("utr12345") == "UTR12345"


def test_tax_reference_rejects_short() -> None:
    with pytest.raises(ValidationError):
        validate_tax_reference("AB12")


def test_tax_band_optional_and_known() -> None:
    assert validate_tax_band(None) is None
    assert validate_tax_band("higher") is TaxBand.HIGHER


def test_tax_band_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        validate_tax_band("ultra")


def test_residency_defaults_to_none() -> None:
    assert validate_residency_status(None) is ResidencyStatus.NONE
    assert validate_residency_status("citizen") is ResidencyStatus.CITIZEN


def test_residency_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        validate_residency_status("alien")


def test_driving_entitlements_parses_csv() -> None:
    result = validate_driving_entitlements("B, C1")
    assert result == frozenset({DrivingEntitlement.B, DrivingEntitlement.C1})


def test_driving_entitlements_accepts_list() -> None:
    result = validate_driving_entitlements(["A", "B"])
    assert result == frozenset({DrivingEntitlement.A, DrivingEntitlement.B})


def test_driving_entitlements_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        validate_driving_entitlements("Z")


def test_driving_restrictions_handles_empty() -> None:
    assert validate_driving_restrictions("") == frozenset()
    assert validate_driving_restrictions(None) == frozenset()


def test_driving_restrictions_parses_codes() -> None:
    assert validate_driving_restrictions("glasses,automatic_only") == frozenset(
        {DrivingRestriction.GLASSES, DrivingRestriction.AUTOMATIC_ONLY}
    )
