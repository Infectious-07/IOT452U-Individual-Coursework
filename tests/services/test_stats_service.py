from datetime import datetime

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.domain.exceptions import AuthorisationError
from digital_id.services.stats_service import StatsService
from tests.conftest import make_new_identity

CENTRAL = OrganisationRole.CENTRAL_AUTHORITY


@pytest.fixture
def setup(wired):
    identity_service, _, _, identities, audit_repo = wired
    stats = StatsService(
        identities,
        audit_repo,
        clock=lambda: datetime(2026, 5, 19, 12, 0, 0),
    )
    return identity_service, stats


def test_snapshot_counts_status_distribution(setup) -> None:
    identity_service, stats = setup
    identity_service.create(CENTRAL, make_new_identity("ID-001"))
    identity_service.create(CENTRAL, make_new_identity("ID-002", name="Alan Turing"))
    identity_service.suspend(CENTRAL, "ID-002")
    snapshot = stats.snapshot(CENTRAL)
    assert snapshot.total == 2
    assert snapshot.by_status == {"ACTIVE": 1, "SUSPENDED": 1, "REVOKED": 0}


def test_snapshot_blocked_for_consumer_roles(setup) -> None:
    _, stats = setup
    with pytest.raises(AuthorisationError):
        stats.snapshot(OrganisationRole.TAX)


def test_recent_event_window(setup) -> None:
    identity_service, stats = setup
    identity_service.create(CENTRAL, make_new_identity())
    snapshot = stats.snapshot(CENTRAL)
    assert isinstance(snapshot.events_last_7_days, int)
    assert snapshot.events_last_7_days >= 0
