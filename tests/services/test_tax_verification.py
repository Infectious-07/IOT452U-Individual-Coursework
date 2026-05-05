from datetime import date

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError, ValidationError

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY
TAX = OrganisationRole.TAX


def test_tax_reports_unknown_identity(wired_services) -> None:
    _, verification, _ = wired_services
    response = verification.verify_for_tax(
        TAX, "ID-999", date(2026, 1, 1), date(2026, 3, 31)
    )
    assert response.exists is False
    assert response.active_now is False
    assert response.suspended_in_period is False


def test_tax_active_identity_clean_period(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 3, 31)
    )
    assert response.exists is True
    assert response.active_now is True
    assert response.suspended_in_period is False


def test_tax_flags_suspension_in_period(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.suspend(CENTRAL, "ID-001")
    identity_service.reactivate(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2026, 1, 1), date(2026, 12, 31)
    )
    assert response.suspended_in_period is True
    assert response.active_now is True


def test_tax_ignores_suspension_outside_period(wired_services) -> None:
    identity_service, verification, _ = wired_services
    identity_service.create(CENTRAL, "ID-001", "Ada Lovelace", "1990-05-01")
    identity_service.suspend(CENTRAL, "ID-001")
    identity_service.reactivate(CENTRAL, "ID-001")
    response = verification.verify_for_tax(
        TAX, "ID-001", date(2030, 1, 1), date(2030, 12, 31)
    )
    assert response.suspended_in_period is False


def test_tax_rejects_inverted_period(wired_services) -> None:
    _, verification, _ = wired_services
    with pytest.raises(ValidationError):
        verification.verify_for_tax(
            TAX, "ID-001", date(2026, 12, 31), date(2026, 1, 1)
        )


def test_tax_check_blocked_for_other_roles(wired_services) -> None:
    _, verification, _ = wired_services
    with pytest.raises(AuthorisationError):
        verification.verify_for_tax(
            OrganisationRole.BANK, "ID-001", date(2026, 1, 1), date(2026, 3, 31)
        )
