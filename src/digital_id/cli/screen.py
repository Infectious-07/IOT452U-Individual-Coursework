from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class Screen:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def clear(self) -> None:
        self._console.clear()

    def header(self, portal_title: str | None, breadcrumb: str | None = None) -> None:
        title = Text("Digital ID Platform", style="bold white on blue")
        if portal_title:
            title.append(Text(f"  ::  {portal_title}", style="white on blue"))
        if breadcrumb:
            title.append(Text(f"  >  {breadcrumb}", style="bold yellow on blue"))
        self._console.print(Panel(title, border_style="blue", padding=(0, 1)))

    def info(self, message: str) -> None:
        self._console.print(message)

    def success(self, message: str) -> None:
        self._console.print(f"[bold green]{message}[/]")

    def warning(self, message: str) -> None:
        self._console.print(f"[bold yellow]{message}[/]")

    def error(self, message: str) -> None:
        self._console.print(f"[bold red]{message}[/]")

    def pause(self) -> None:
        # rich console makes this trivial cross platform
        self._console.input("[dim]press enter to continue[/]")

    @property
    def console(self) -> Console:
        return self._console
