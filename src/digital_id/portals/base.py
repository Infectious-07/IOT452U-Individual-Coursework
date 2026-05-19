from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..authorisation.roles import OrganisationRole

CommandResult = Any
CommandHandler = Callable[[Mapping[str, str]], CommandResult]
Validator = Callable[[str], object]


@dataclass(frozen=True)
class Argument:
    key: str
    label: str
    default: str | None = None
    validator: Validator | None = None
    options: tuple[str, ...] | None = None
    multi_select: bool = False


@dataclass(frozen=True)
class Command:
    key: str
    label: str
    description: str
    arguments: Sequence[Argument]
    handler: CommandHandler
    confirmation: str | None = None
    group: str = ""


@dataclass
class Portal:
    role: OrganisationRole
    title: str
    description: str = ""
    _commands: list[Command] = field(default_factory=list)

    def add(self, command: Command) -> None:
        self._commands.append(command)

    @property
    def commands(self) -> Sequence[Command]:
        return tuple(self._commands)

    def find(self, key: str) -> Command | None:
        for command in self._commands:
            if command.key == key:
                return command
        return None
