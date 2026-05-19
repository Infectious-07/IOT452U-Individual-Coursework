from __future__ import annotations

import shlex
from collections.abc import Callable, Mapping
from typing import TextIO

from ..authorisation.roles import OrganisationRole
from ..domain.exceptions import DigitalIdError
from ..portals.base import Portal


class Shell:
    def __init__(
        self,
        portals: Mapping[OrganisationRole, Portal],
        reader: Callable[[str], str] = input,
        writer: TextIO | None = None,
    ) -> None:
        self._portals = dict(portals)
        self._reader = reader
        self._writer = writer
        self._active: Portal | None = None

    def _write(self, line: str = "") -> None:
        if self._writer is None:
            print(line)
        else:
            self._writer.write(line + "\n")

    def _select_portal(self) -> bool:
        self._write("Available portals:")
        for index, role in enumerate(self._portals, start=1):
            portal = self._portals[role]
            self._write(f"  {index}. {portal.title} ({role.value})")
        self._write("Type a number to enter a portal, or quit to exit.")
        choice = self._reader("portal> ").strip()
        if choice in {"quit", "exit"}:
            return False
        try:
            index = int(choice)
            role = list(self._portals.keys())[index - 1]
        except (ValueError, IndexError):
            self._write("unknown portal selection")
            return True
        self._active = self._portals[role]
        self._write(f"entered {self._active.title}; type help for commands")
        return True

    def _prompt(self) -> str:
        if self._active is None:
            return "portal> "
        return f"{self._active.role.value.lower()}> "

    def _run_command(self, line: str) -> bool:
        if not line:
            return True
        tokens = shlex.split(line)
        if not tokens:
            return True
        name, *args = tokens
        if name in {"quit", "exit"}:
            return False
        if name == "portal":
            self._active = None
            return True
        if self._active is None:
            self._write("no portal selected; pick one to continue")
            return True
        if name == "help":
            for row in self._active.help_lines():
                self._write(row)
            return True
        try:
            self._active.dispatch(name, args)
        except KeyError:
            self._write(f"unknown command: {name}")
        except DigitalIdError as err:
            self._write(f"rejected: {err}")
        except ValueError as err:
            # usage and parsing errors carry their own prefix, so we print as-is
            self._write(str(err))
        return True

    def run(self) -> None:
        self._write("Digital ID console; type help inside a portal or quit to exit")
        try:
            while True:
                if self._active is None:
                    if not self._select_portal():
                        return
                    continue
                try:
                    line = self._reader(self._prompt())
                except EOFError:
                    return
                if not self._run_command(line.strip()):
                    return
        except KeyboardInterrupt:
            self._write("")
            return
