import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import (
    AuthorisationError,
    DuplicateIdentityError,
    InvalidTransitionError,
    ValidationError,
)
from digital_id.domain.identity import IdentityStatus
from digital_id.services.identity_service import IdentityService

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
BANK = OrganisationRole.BANK


def test_create_returns_active_identity(identity_service: IdentityService) -> None:
    identity = identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    assert identity.id == "ID-001"
    assert identity.status is IdentityStatus.ACTIVE


def test_create_rejects_non_central_actor(identity_service: IdentityService) -> None:
    with pytest.raises(AuthorisationError):
        identity_service.create(BANK, "ID-001", "Ada Lovelace", "1990-05-01")


def test_create_rejects_bad_input(identity_service: IdentityService) -> None:
    with pytest.raises(ValidationError):
        identity_service.create(CENTRAL, "AB", "Ada Lovelace", "1990-05-01")


def test_create_rejects_duplicates(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    with pytest.raises(DuplicateIdentityError):
        identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")


def test_update_name_writes_new_value(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    updated = identity_service.update_name(CENTRAL, "ID-001", "Ada L.")
    assert updated.name == "Ada L."


def test_update_name_is_idempotent(identity_service: IdentityService) -> None:
    created = identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    again = identity_service.update_name(CENTRAL, "ID-001", "Ada Lovelace")
    assert again == created


def test_update_name_blocked_on_revoked(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.update_name(CENTRAL, "ID-001", "Ada L.")


def test_suspend_and_reactivate(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    suspended = identity_service.suspend(CENTRAL, "ID-001")
    assert suspended.status is IdentityStatus.SUSPENDED
    reactivated = identity_service.reactivate(CENTRAL, "ID-001")
    assert reactivated.status is IdentityStatus.ACTIVE


def test_suspend_is_idempotent(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    first = identity_service.suspend(CENTRAL, "ID-001")
    second = identity_service.suspend(CENTRAL, "ID-001")
    assert first.status is IdentityStatus.SUSPENDED
    assert second.status is IdentityStatus.SUSPENDED


def test_revoked_is_terminal(identity_service: IdentityService) -> None:
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.reactivate(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.suspend(CENTRAL, "ID-001")
