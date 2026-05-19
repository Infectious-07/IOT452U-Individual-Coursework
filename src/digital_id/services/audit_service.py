from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from ..clock import utc_now
from ..domain.identity import AuditAction, AuditEvent
from ..domain.roles import OrganisationRole
from ..persistence.audit_repository import AuditRepository


class AuditService:
    def __init__(
        self,
        events: AuditRepository,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._events = events
        self._clock = clock

    def record(
        self,
        actor: OrganisationRole,
        action: AuditAction,
        identity_id: str | None,
        payload: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            occurred_at=self._clock(),
            actor_role=actor.value,
            action=action,
            identity_id=identity_id,
            payload=dict(payload or {}),
        )
        self._events.append(event)
        return event

    def history_for(self, identity_id: str) -> list[AuditEvent]:
        return list(self._events.list_for_identity(identity_id))

    def events_between(
        self, start: datetime, end: datetime, identity_id: str | None = None
    ) -> list[AuditEvent]:
        return list(self._events.list_between(start, end, identity_id))
