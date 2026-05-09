import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


def test_dvla_active_identity(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.exists is True
    assert response.active_now is True
    assert response.restricted_now is False


def test_dvla_suspended_identity_is_restricted(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.active_now is False
    assert response.restricted_now is True


def test_dvla_revoked_identity_neither_active_nor_restricted(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.active_now is False
    assert response.restricted_now is False


def test_bank_returns_valid_now_only(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    response = verification.verify_validity(OrganisationRole.BANK, "ID-001")
    assert response.valid_now is True
    # response shape carries only id and valid_now
    assert set(response.__dataclass_fields__) == {"identity_id", "valid_now"}


def test_employer_response_for_suspended(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_validity(OrganisationRole.EMPLOYER, "ID-001")
    assert response.valid_now is False


def test_validity_rejects_other_roles(wired_services) -> None:
    _, verification, _ = wired_services
    with pytest.raises(AuthorisationError):
        verification.verify_validity(OrganisationRole.TAX, "ID-001")


def test_welfare_lookup_returns_name_when_valid(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    response = verification.verify_lookup(OrganisationRole.WELFARE, "ID-001")
    assert response.valid_now is True
    assert response.name == "Ada Lovelace"


def test_local_authority_lookup_hides_name_when_invalid(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_lookup(OrganisationRole.LOCAL_AUTHORITY, "ID-001")
    assert response.valid_now is False
    assert response.name is None


def test_lookup_rejects_bank(wired_services) -> None:
    _, verification, _ = wired_services
    with pytest.raises(AuthorisationError):
        verification.verify_lookup(OrganisationRole.BANK, "ID-001")
