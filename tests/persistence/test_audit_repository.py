from datetime import datetime
from pathlib import Path

import pytest

from digital_id.domain.audit import AuditAction, AuditEvent
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect


@pytest.fixture
def repo(tmp_path: Path) -> AuditRepository:
    connection = connect(tmp_path / "audit.sqlite")
    bootstrap(connection)
    return AuditRepository(connection)


def make_event(when: datetime, action: AuditAction, identity_id: str = "ID-001") -> AuditEvent:
    return AuditEvent(
        occurred_at=when,
        actor_role="CENTRAL_AUTHORITY",
        action=action,
        identity_id=identity_id,
        payload={"note": action.value},
    )


def test_append_persists_event(repo: AuditRepository) -> None:
    event = make_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE)
    repo.append(event)
    fetched = list(repo.list_for_identity("ID-001"))
    assert len(fetched) == 1
    assert fetched[0].action is AuditAction.CREATE
    assert fetched[0].payload == {"note": "CREATE"}


def test_list_for_identity_orders_by_time(repo: AuditRepository) -> None:
    repo.append(make_event(datetime(2026, 1, 2, 10, 0), AuditAction.SUSPEND))
    repo.append(make_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE))
    actions = [event.action for event in repo.list_for_identity("ID-001")]
    assert actions == [AuditAction.CREATE, AuditAction.SUSPEND]


def test_list_between_filters_by_period(repo: AuditRepository) -> None:
    repo.append(make_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE))
    repo.append(make_event(datetime(2026, 6, 1, 10, 0), AuditAction.SUSPEND))
    repo.append(make_event(datetime(2026, 12, 1, 10, 0), AuditAction.REACTIVATE))
    middle = list(
        repo.list_between(datetime(2026, 5, 1), datetime(2026, 7, 1), "ID-001")
    )
    assert len(middle) == 1
    assert middle[0].action is AuditAction.SUSPEND


def test_list_between_without_id_returns_all(repo: AuditRepository) -> None:
    repo.append(make_event(datetime(2026, 1, 1, 10, 0), AuditAction.CREATE, "ID-A"))
    repo.append(make_event(datetime(2026, 1, 2, 10, 0), AuditAction.CREATE, "ID-B"))
    events = list(repo.list_between(datetime(2026, 1, 1), datetime(2026, 1, 3)))
    assert {event.identity_id for event in events} == {"ID-A", "ID-B"}
