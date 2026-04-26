from datetime import date, timedelta

import pytest

from digital_id.domain.exceptions import ValidationError
from digital_id.domain.validators import (
    validate_dob,
    validate_identity_id,
    validate_name,
)


def test_validate_identity_id_normalises_to_upper() -> None:
    assert validate_identity_id("id-001") == "ID-001"


def test_validate_identity_id_rejects_short_value() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_identity_id("ab")
    assert excinfo.value.field == "id"


def test_validate_identity_id_rejects_unsupported_chars() -> None:
    with pytest.raises(ValidationError):
        validate_identity_id("ID 001")


def test_validate_name_trims_and_accepts() -> None:
    assert validate_name("  Ada Lovelace  ") == "Ada Lovelace"


def test_validate_name_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        validate_name("")


def test_validate_name_rejects_digits() -> None:
    with pytest.raises(ValidationError):
        validate_name("Ada 9")


def test_validate_dob_accepts_iso() -> None:
    assert validate_dob("1990-05-01") == date(1990, 5, 1)


def test_validate_dob_rejects_future() -> None:
    future = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        validate_dob(future)


def test_validate_dob_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        validate_dob("not-a-date")
