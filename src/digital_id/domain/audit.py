from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping


class AuditAction(str, Enum):
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
