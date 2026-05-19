from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from . import theme

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
                Text(BANNER, style=theme.ACCENT, justify="center"),
                title=f"[{theme.HEADER_STYLE}]Identity Management Platform[/]",
                subtitle=f"[{theme.MUTED}]v1.0.0[/]",
                border_style=theme.BORDER,
                padding=(0, 2),
            )
        )
        self._console.print()

    def header(self, portal_title: str | None, breadcrumb: str | None = None) -> None:
        parts: list[str] = []
        if portal_title:
            parts.append(f"[{theme.ACCENT}]{portal_title}[/]")
        if breadcrumb:
            parts.append(f"[{theme.ACCENT2}]{breadcrumb}[/]")
        sep = f"  [{theme.MUTED}]>[/]  "
        label = sep.join(parts) if parts else f"[{theme.HEADER_STYLE}]Digital ID Platform[/]"
        self._console.print(
            Panel(label, border_style=theme.BORDER_DIM, padding=(0, 2))
        )
        self._console.print()

    def rule(self, label: str = "") -> None:
        self._console.print(Rule(label, style=theme.BORDER_DIM))

    def info(self, message: str) -> None:
        self._console.print(message)

    def success(self, message: str) -> None:
        self._console.print(f"[{theme.SUCCESS}]{message}[/]")

    def warning(self, message: str) -> None:
        self._console.print(f"[{theme.WARNING}]{message}[/]")

    def error(self, message: str) -> None:
        self._console.print(f"[{theme.ERROR}]{message}[/]")

    def goodbye(self) -> None:
        self._console.print()
        self._console.print(
            Panel(
                f"[{theme.ACCENT}]Thank you for using the Digital ID Platform.[/]",
                border_style=theme.BORDER,
                padding=(1, 4),
            )
        )
        self._console.print()

    def pause(self) -> None:
        self._console.input(f"[{theme.MUTED}]press enter to continue[/]")

    @property
    def console(self) -> Console:
        return self._console
