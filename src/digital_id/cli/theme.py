from __future__ import annotations

from ..domain.identity import IdentityStatus

STATUS_COLOUR = {
    IdentityStatus.ACTIVE: "bold green",
    IdentityStatus.SUSPENDED: "bold yellow",
    IdentityStatus.REVOKED: "bold red",
}

ACCENT = "bold cyan"
ACCENT2 = "bold magenta"
MUTED = "dim"
HEADER_STYLE = "bold white"
BORDER = "bright_cyan"
BORDER_DIM = "cyan"
SUCCESS = "bold green"
WARNING = "bold yellow"
ERROR = "bold red"


def colour_status(status: IdentityStatus) -> str:
    return STATUS_COLOUR.get(status, "white")
