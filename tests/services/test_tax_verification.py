from datetime import date

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError, ValidationError
from digital_id.domain.identity import TaxBand
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
TAX = OrganisationRole.TAX


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


def test_tax_clean_period_returns_band(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service, TaxBand.HIGHER)
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 3, 31)
    )
    assert response.exists is True
    assert response.active_now is True
    assert response.suspended_in_period is False
    assert response.tax_band is TaxBand.HIGHER
    assert response.tax_reference == "UTR12345"


def test_tax_flags_suspension_in_period(wired) -> None:
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


def test_tax_rejects_inverted_period(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(ValidationError):
        verification.verify_for_tax(
            TAX, "ID-001", date(2026, 12, 31), date(2026, 1, 1)
        )


def test_tax_check_blocked_for_other_roles(wired) -> None:
    _, verification, *_ = wired
    with pytest.raises(AuthorisationError):
        verification.verify_for_tax(
            OrganisationRole.BANK, "ID-001", date(2026, 1, 1), date(2026, 3, 31)
        )


def test_tax_flags_suspension_starting_before_period(wired) -> None:
    identity_service, verification, *_ = wired
    _create_with_tax(identity_service)
    identity_service.suspend(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 12, 31)
    )
    assert response.suspended_in_period is True
