import pytest

from digital_id.domain.exceptions import (
    AuthorisationError,
    DigitalIdError,
    DuplicateIdentityError,
    IdentityNotFoundError,
    InvalidTransitionError,
    ValidationError,
)


def test_all_errors_inherit_from_base() -> None:
    subclasses = [
        IdentityNotFoundError("ID-001"),
        DuplicateIdentityError("ID-001"),
        InvalidTransitionError("ACTIVE", "REVOKED"),
        ValidationError("name", "empty"),
        AuthorisationError("BANK", "create"),
    ]
    for exc in subclasses:
        assert isinstance(exc, DigitalIdError)


def test_messages_include_context() -> None:
    err = InvalidTransitionError("ACTIVE", "REVOKED")
    assert "ACTIVE" in str(err)
    assert "REVOKED" in str(err)


def test_authorisation_error_carries_role_and_action() -> None:
    err = AuthorisationError("BANK", "create")
    assert err.role == "BANK"
    assert err.action == "create"


def test_base_error_is_an_exception() -> None:
    with pytest.raises(DigitalIdError):
        raise DigitalIdError("boom")
