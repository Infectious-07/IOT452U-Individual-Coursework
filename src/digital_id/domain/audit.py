from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AuditAction(StrEnum):
    # lifecycle actions, owned by the central authority
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    SUSPEND = "SUSPEND"
    REVOKE = "REVOKE"
    REACTIVATE = "REACTIVATE"
    # consumer verification actions
    VERIFY = "VERIFY"


@dataclass(frozen=True)
class AuditEvent:
    occurred_at: datetime
    actor_role: str
    action: AuditAction
    identity_id: str | None
    payload: Mapping[str, Any] = field(default_factory=dict)
