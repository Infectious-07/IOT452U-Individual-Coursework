from __future__ import annotations

from ..domain.identity import IdentityStatus

# colour names follow rich's standard markup so they render across platforms
STATUS_COLOUR = {
    IdentityStatus.ACTIVE: "bold green",
    IdentityStatus.SUSPENDED: "bold yellow",
    IdentityStatus.REVOKED: "bold red",
}

ACCENT = "bold cyan"
MUTED = "grey50"
HEADER_BG = "on blue"
ERROR = "bold red"
SUCCESS = "bold green"
WARNING = "bold yellow"


def colour_status(status: IdentityStatus) -> str:
    return STATUS_COLOUR.get(status, "white")
