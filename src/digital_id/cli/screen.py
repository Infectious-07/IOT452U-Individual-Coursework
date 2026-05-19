from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

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

BANNER = r"""
 ▓█████▄  ██▓  ▄████  ██▓▄▄▄█████▓ ▄▄▄       ██▓        ██▓▓█████▄
 ▒██▀ ██▌▓██▒ ██▒ ▀█▒▓██▒▓  ██▒ ▓▒▒████▄    ▓██▒       ▓██▒▒██▀ ██▌
 ░██   █▌▒██▒▒██░▄▄▄░▒██▒▒ ▓██░ ▒░▒██  ▀█▄  ▒██░       ▒██▒░██   █▌
 ░▓█▄   ▌░██░░▓█  ██▓░██░░ ▓██▓ ░ ░██▄▄▄▄██ ▒██░       ░██░░▓█▄   ▌
 ░▒████▓ ░██░░▒▓███▀▒░██░  ▒██▒ ░  ▓█   ▓██▒░██████▒   ░██░░▒████▓
  ▒▒▓  ▒ ░▓   ░▒   ▒ ░▓    ▒ ░░    ▒▒   ▓▒█░░ ▒░▓  ░   ░▓   ▒▒▓  ▒
  ░ ▒  ▒  ▒ ░  ░   ░  ▒ ░    ░      ▒   ▒▒ ░░ ░ ▒  ░    ▒ ░ ░ ▒  ▒
  ░ ░  ░  ▒ ░░ ░   ░  ▒ ░  ░        ░   ▒     ░ ░       ▒ ░ ░ ░  ░
    ░     ░        ░  ░                 ░  ░    ░  ░    ░     ░
  ░                                                         ░
"""


class Screen:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def clear(self) -> None:
        self._console.clear()

    def banner(self) -> None:
        self._console.print()
        self._console.print(
            Panel(
                Text(BANNER, style=ACCENT, justify="center"),
                title=f"[{HEADER_STYLE}]Identity Management Platform[/]",
                subtitle=f"[{MUTED}]v1.0.0[/]",
                border_style=BORDER,
                padding=(0, 2),
            )
        )
        self._console.print()

    def header(self, portal_title: str | None, breadcrumb: str | None = None) -> None:
        parts: list[str] = []
        if portal_title:
            parts.append(f"[{ACCENT}]{portal_title}[/]")
        if breadcrumb:
            parts.append(f"[{ACCENT2}]{breadcrumb}[/]")
        sep = f"  [{MUTED}]>[/]  "
        label = sep.join(parts) if parts else f"[{HEADER_STYLE}]Digital ID Platform[/]"
        self._console.print(
            Panel(label, border_style=BORDER_DIM, padding=(0, 2))
        )
        self._console.print()

    def rule(self, label: str = "") -> None:
        self._console.print(Rule(label, style=BORDER_DIM))

    def info(self, message: str) -> None:
        self._console.print(message)

    def success(self, message: str) -> None:
        self._console.print(f"[{SUCCESS}]{message}[/]")

    def warning(self, message: str) -> None:
        self._console.print(f"[{WARNING}]{message}[/]")

    def error(self, message: str) -> None:
        self._console.print(f"[{ERROR}]{message}[/]")

    def goodbye(self) -> None:
        self._console.print()
        self._console.print(
            Panel(
                f"[{ACCENT}]Thank you for using the Digital ID Platform.[/]",
                border_style=BORDER,
                padding=(1, 4),
            )
        )
        self._console.print()

    def pause(self) -> None:
        self._console.input(f"[{MUTED}]press enter to continue[/]")

    @property
    def console(self) -> Console:
        return self._console
