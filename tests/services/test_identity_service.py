import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import (
    AuthorisationError,
    DuplicateIdentityError,
    InvalidTransitionError,
    ValidationError,
)
from digital_id.domain.identity import IdentityStatus, ResidencyStatus, TaxBand
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
CONSUMER = OrganisationRole.EMPLOYER


def test_create_returns_active_identity(wired) -> None:
    identity_service, *_ = wired
    identity = identity_service.create(CENTRAL, make_new_identity())
    assert identity.id == "ID-001"
    assert identity.status is IdentityStatus.ACTIVE
    assert identity.nationality == "GB"


def test_create_rejects_non_central_actor(wired) -> None:
    identity_service, *_ = wired
    with pytest.raises(AuthorisationError):
        identity_service.create(CONSUMER, make_new_identity())


def test_create_rejects_bad_input(wired) -> None:
    identity_service, *_ = wired
    with pytest.raises(ValidationError):
        identity_service.create(CENTRAL, make_new_identity(identity_id="AB"))


def test_create_rejects_duplicates(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    with pytest.raises(DuplicateIdentityError):
        identity_service.create(CENTRAL, make_new_identity())


def test_update_name_writes_new_value(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_name(CENTRAL, "ID-001", "Ada L.")
    assert updated.name == "Ada L."


def test_update_address(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_address(CENTRAL, "ID-001", "Bletchley Park")
    assert updated.address == "Bletchley Park"


def test_update_tax_details(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_tax_details(CENTRAL, "ID-001", "utr12345", "higher")
    assert updated.tax_reference == "UTR12345"
    assert updated.tax_band is TaxBand.HIGHER


def test_update_driving_set(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_driving(CENTRAL, "ID-001", "B,C1", "GLASSES")
    assert "B" in {entitlement.value for entitlement in updated.driving_entitlements}


def test_update_eligibility(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    updated = identity_service.update_eligibility(CENTRAL, "ID-001", True, "RESIDENT")
    assert updated.right_to_work is True
    assert updated.residency_status is ResidencyStatus.RESIDENT


def test_update_name_blocked_on_revoked(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.update_name(CENTRAL, "ID-001", "Ada L.")


def test_suspend_and_reactivate(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    suspended = identity_service.suspend(CENTRAL, "ID-001")
    reactivated = identity_service.reactivate(CENTRAL, "ID-001")
    assert suspended.status is IdentityStatus.SUSPENDED
    assert reactivated.status is IdentityStatus.ACTIVE


def test_revoked_is_terminal(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    with pytest.raises(InvalidTransitionError):
        identity_service.reactivate(CENTRAL, "ID-001")


def test_list_all(wired) -> None:
    identity_service, *_ = wired
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    listing = identity_service.list_all()
    assert {item.id for item in listing} == {"ID-001", "ID-002"}
