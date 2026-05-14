from __future__ import annotations

from datetime import UTC, datetime


# returns a naive UTC datetime, preserving the existing storage shape while
# avoiding the deprecation warning emitted by datetime.utcnow on Python 3.12+
def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
