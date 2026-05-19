from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

BANNER = r"""
  ____  _       _ _        _   ___ ____
 |  _ \(_) __ _(_) |_ __ _| | |_ _|  _ \
 | | | | |/ _` | | __/ _` | |  | || | | |
 | |_| | | (_| | | || (_| | |  | || |_| |
 |____/|_|\__, |_|\__\__,_|_| |___|____/
          |___/
"""


class Screen:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def clear(self) -> None:
        self._console.clear()

    def banner(self) -> None:
        self._console.print(
            Panel(
                Text(BANNER, style="bold cyan", justify="center"),
                title="[bold white]Identity Management Platform[/]",
                subtitle="[dim]v1.0.0[/]",
                border_style="cyan",
                padding=(0, 2),
            )
        )

    def header(self, portal_title: str | None, breadcrumb: str | None = None) -> None:
        parts: list[str] = []
        if portal_title:
            parts.append(f"[bold white]{portal_title}[/]")
        if breadcrumb:
            parts.append(f"[bold yellow]{breadcrumb}[/]")
        label = "  >  ".join(parts) if parts else "[bold white]Digital ID Platform[/]"
        self._console.print(Panel(label, border_style="blue", padding=(0, 1)))

    def rule(self, label: str = "") -> None:
        self._console.print(Rule(label, style="dim"))

    def info(self, message: str) -> None:
        self._console.print(message)

    def success(self, message: str) -> None:
        self._console.print(f"[bold green]{message}[/]")

    def warning(self, message: str) -> None:
        self._console.print(f"[bold yellow]{message}[/]")

    def error(self, message: str) -> None:
        self._console.print(f"[bold red]{message}[/]")

    def goodbye(self) -> None:
        self._console.print()
        self._console.print(
            Panel(
                "[bold cyan]Thank you for using the Digital ID Platform.[/]",
                border_style="cyan",
                padding=(0, 2),
            )
        )

    def pause(self) -> None:
        self._console.input("[dim]press enter to continue[/]")

    @property
    def console(self) -> Console:
        return self._console
