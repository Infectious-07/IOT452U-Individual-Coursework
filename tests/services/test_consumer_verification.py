import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError
from digital_id.domain.identity import DrivingEntitlement, ResidencyStatus
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


def test_dvla_active_identity_with_entitlements(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(
        CENTRAL, make_new_identity(driving_entitlements=["B", "C1"])
    )
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.exists is True
    assert response.active_now is True
    assert response.restricted_now is False
    assert DrivingEntitlement.B in response.entitlements
    assert DrivingEntitlement.C1 in response.entitlements


def test_dvla_suspended_identity_is_restricted(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.restricted_now is True


def test_bank_returns_valid_now_only(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    response = verification.verify_for_bank(OrganisationRole.BANK, "ID-001")
    assert response.valid_now is True


def test_employer_returns_right_to_work(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(right_to_work=True))
    response = verification.verify_for_employer(OrganisationRole.EMPLOYER, "ID-001")
    assert response.valid_now is True
    assert response.right_to_work is True


def test_employer_drops_right_to_work_on_invalid(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(right_to_work=True))
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_for_employer(OrganisationRole.EMPLOYER, "ID-001")
    assert response.valid_now is False
    assert response.right_to_work is False


def test_bank_rejects_other_roles(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(AuthorisationError):
        verification.verify_for_bank(OrganisationRole.TAX, "ID-001")


def test_employer_rejects_other_roles(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(AuthorisationError):
        verification.verify_for_employer(OrganisationRole.TAX, "ID-001")


def test_welfare_lookup_returns_name_and_residency(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(
        CENTRAL, make_new_identity(residency_status="CITIZEN")
    )
    response = verification.verify_lookup(OrganisationRole.WELFARE, "ID-001")
    assert response.valid_now is True
    assert response.name == "Ada Lovelace"
    assert response.residency_status is ResidencyStatus.CITIZEN


def test_local_authority_lookup_hides_name_when_invalid(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_lookup(OrganisationRole.LOCAL_AUTHORITY, "ID-001")
    assert response.valid_now is False
    assert response.name is None
    assert response.residency_status is None


def test_lookup_rejects_bank(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(AuthorisationError):
        verification.verify_lookup(OrganisationRole.BANK, "ID-001")
