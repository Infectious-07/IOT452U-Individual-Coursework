import pytest

from digital_id.authorisation.roles import OrganisationRole, is_allowed, require
from digital_id.domain.exceptions import AuthorisationError

CONSUMER_ROLES = [
    OrganisationRole.TAX,
    OrganisationRole.DVLA,
    OrganisationRole.BANK,
    OrganisationRole.EMPLOYER,
    OrganisationRole.WELFARE,
    OrganisationRole.LOCAL_AUTHORITY,
    OrganisationRole.IMMIGRATION,
]


@pytest.mark.parametrize("action", ["create", "update", "suspend", "revoke", "reactivate"])
def test_central_authority_can_run_lifecycle_actions(action: str) -> None:
    assert is_allowed(OrganisationRole.CENTRAL_AUTHORITY, action) is True


@pytest.mark.parametrize("role", CONSUMER_ROLES)
@pytest.mark.parametrize("action", ["create", "update", "suspend", "revoke", "reactivate"])
def test_consumer_roles_cannot_run_lifecycle_actions(
    role: OrganisationRole, action: str
) -> None:
    assert is_allowed(role, action) is False


@pytest.mark.parametrize("role", CONSUMER_ROLES + [OrganisationRole.CENTRAL_AUTHORITY])
def test_every_role_can_verify(role: OrganisationRole) -> None:
    assert is_allowed(role, "verify") is True


def test_require_raises_authorisation_error_for_disallowed() -> None:
    with pytest.raises(AuthorisationError) as excinfo:
        require(OrganisationRole.BANK, "create")
    assert excinfo.value.role == "BANK"
    assert excinfo.value.action == "create"


def test_require_passes_for_allowed() -> None:
    require(OrganisationRole.CENTRAL_AUTHORITY, "create")
