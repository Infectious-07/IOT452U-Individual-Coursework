from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..authorisation.roles import OrganisationRole

# a portal command is a callable that receives the parsed args and prints output
Handler = Callable[[list[str]], None]


@dataclass(frozen=True)
class Command:
    name: str
    summary: str
    handler: Handler


class Portal:
    role: OrganisationRole
    title: str

    def __init__(self, role: OrganisationRole, title: str) -> None:
        self.role = role
        self.title = title
        self._commands: dict[str, Command] = {}

    def register(self, name: str, summary: str, handler: Handler) -> None:
        self._commands[name] = Command(name=name, summary=summary, handler=handler)

    def commands(self) -> Mapping[str, Command]:
        return self._commands

    def dispatch(self, name: str, args: list[str]) -> None:
        command = self._commands.get(name)
        if command is None:
            raise KeyError(name)
        command.handler(args)

    def help_lines(self) -> list[str]:
        rows: list[str] = [f"{self.title} ({self.role.value})", ""]
        for command in self._commands.values():
            rows.append(f"  {command.name:<14} {command.summary}")
        rows.append("  help           show this list")
        rows.append("  portal         go back to portal selection")
        rows.append("  quit           leave the shell")
        return rows


def render_kv(items: Mapping[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in items.items())
