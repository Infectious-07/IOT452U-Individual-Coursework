import pytest

from digital_id.domain.exceptions import InvalidTransitionError
from digital_id.domain.identity import IdentityStatus
from digital_id.domain.transitions import assert_allowed, is_allowed


@pytest.mark.parametrize(
    "current,target,expected",
    [
        (IdentityStatus.ACTIVE, IdentityStatus.SUSPENDED, True),
        (IdentityStatus.ACTIVE, IdentityStatus.REVOKED, True),
        (IdentityStatus.SUSPENDED, IdentityStatus.ACTIVE, True),
        (IdentityStatus.SUSPENDED, IdentityStatus.REVOKED, True),
        (IdentityStatus.ACTIVE, IdentityStatus.ACTIVE, True),
        (IdentityStatus.REVOKED, IdentityStatus.ACTIVE, False),
        (IdentityStatus.REVOKED, IdentityStatus.SUSPENDED, False),
        (IdentityStatus.REVOKED, IdentityStatus.REVOKED, True),
    ],
)
def test_is_allowed_table(current: IdentityStatus, target: IdentityStatus, expected: bool) -> None:
    assert is_allowed(current, target) is expected


def test_assert_allowed_raises_on_forbidden_move() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_allowed(IdentityStatus.REVOKED, IdentityStatus.ACTIVE)
