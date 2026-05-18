from datetime import date

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError, ValidationError
from digital_id.domain.identity import DrivingEntitlement, ResidencyStatus, TaxBand
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
TAX = OrganisationRole.TAX


# tax authority

def _create_with_tax(identity_service, band: TaxBand | None = TaxBand.BASIC) -> None:
    identity_service.create(
        CENTRAL,
        make_new_identity(
            tax_reference="UTR12345",
            tax_band=band.value if band else None,
        ),
    )


def test_tax_reports_unknown_identity(wired) -> None:
    _, verification, *_ = wired
    response = verification.verify_for_tax(
        TAX, "ID-999", date(2026, 1, 1), date(2026, 3, 31)
    )
    assert response.exists is False
    assert response.tax_reference is None


def test_tax_returns_band_for_clean_period(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service, TaxBand.HIGHER)
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 3, 31)
    )
    assert response.active_now is True
    assert response.suspended_in_period is False
    assert response.tax_band is TaxBand.HIGHER


def test_tax_flags_suspension_inside_period(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service)
    identity_service.suspend(CENTRAL, "ID-001")
    identity_service.reactivate(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 12, 31)
    )
    assert response.suspended_in_period is True


def test_tax_ignores_suspension_outside_period(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service)
    identity_service.suspend(CENTRAL, "ID-001")
    identity_service.reactivate(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2030, 1, 1), date(2030, 12, 31)
    )
    assert response.suspended_in_period is False


def test_tax_flags_suspension_starting_before_period(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service)
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 12, 31)
    )
    assert response.suspended_in_period is True


def test_tax_rejects_inverted_period(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(ValidationError):
        verification.verify_for_tax(
            TAX, "ID-001", date(2026, 12, 31), date(2026, 1, 1)
        )


# dvla

def test_dvla_returns_entitlements_for_active_identity(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(
        CENTRAL, make_new_identity(driving_entitlements=["B", "C1"])
    )
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.active_now is True
    assert response.restricted_now is False
    assert DrivingEntitlement.B in response.entitlements


def test_dvla_marks_suspended_as_restricted(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_for_dvla(OrganisationRole.DVLA, "ID-001")
    assert response.restricted_now is True


# bank and employer

def test_bank_returns_valid_now_only(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    response = verification.verify_for_bank(OrganisationRole.BANK, "ID-001")
    assert response.valid_now is True


def test_employer_returns_right_to_work(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(right_to_work=True))
    response = verification.verify_for_employer(OrganisationRole.EMPLOYER, "ID-001")
    assert response.right_to_work is True


def test_employer_drops_right_to_work_when_invalid(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(right_to_work=True))
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_for_employer(OrganisationRole.EMPLOYER, "ID-001")
    assert response.valid_now is False
    assert response.right_to_work is False


# lookup

def test_welfare_lookup_returns_name_and_residency(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity(residency_status="CITIZEN"))
    response = verification.verify_lookup(OrganisationRole.WELFARE, "ID-001")
    assert response.name == "Ada Lovelace"
    assert response.residency_status is ResidencyStatus.CITIZEN


def test_local_authority_lookup_hides_name_when_invalid(wired) -> None:
    identity_service, verification, *_ = wired
    identity_service.create(CENTRAL, make_new_identity())
    identity_service.revoke(CENTRAL, "ID-001")
    response = verification.verify_lookup(OrganisationRole.LOCAL_AUTHORITY, "ID-001")
    assert response.valid_now is False
    assert response.name is None


# cross role authorisation

@pytest.mark.parametrize(
    "method,role,kwargs",
    [
        ("verify_for_tax", OrganisationRole.BANK, {"period_start": date(2026, 1, 1), "period_end": date(2026, 3, 31)}),
        ("verify_for_dvla", OrganisationRole.BANK, {}),
        ("verify_for_bank", OrganisationRole.TAX, {}),
        ("verify_for_employer", OrganisationRole.TAX, {}),
        ("verify_lookup", OrganisationRole.BANK, {}),
    ],
)
def test_each_endpoint_blocks_other_roles(wired, method, role, kwargs) -> None:
    _, verification, *_ = wired
    func = getattr(verification, method)
    with pytest.raises(AuthorisationError):
        func(role, "ID-001", **kwargs)
