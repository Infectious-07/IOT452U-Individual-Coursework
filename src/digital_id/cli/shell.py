from __future__ import annotations

from collections.abc import Mapping

from ..authorisation.roles import OrganisationRole
from ..domain.exceptions import DigitalIdError
from ..portals.base import Argument, Portal
from .prompter import Choice, Prompter, QuestionaryPrompter, Separator
from .screen import Screen

_BACK = "__back__"
_EXIT = "__exit__"
_MAX_ATTEMPTS = 3

GROUP_PREFIX = {
    "Records": "●",
    "Updates": "◆",
    "Lifecycle": "▲",
    "Reports": "■",
}


class MenuShell:
    def __init__(
        self,
        portals: Mapping[OrganisationRole, Portal],
        prompter: Prompter | None = None,
        screen: Screen | None = None,
        pause_between_actions: bool = True,
    ) -> None:
        self._portals = list(portals.values())
        self._prompter = prompter or QuestionaryPrompter()
        self._screen = screen or Screen()
        self._pause = pause_between_actions

    def run(self) -> None:
        self._screen.clear()
        self._screen.banner()
        while True:
            choice = self._pick_portal()
            if choice is None or choice == _EXIT:
                self._screen.clear()
                self._screen.goodbye()
                return
            portal = self._portal_by_role(choice)
            if portal is None:
                continue
            self._portal_loop(portal)

    def _pick_portal(self) -> str | None:
        self._screen.rule("Select a portal")
        choices: list[Choice | Separator] = [
            Choice(portal.title, portal.role.value, portal.description)
            for portal in self._portals
        ]
        choices.append(Separator())
        choices.append(Choice("Exit", _EXIT))
        return self._prompter.choose("Portal", choices)

    def _portal_by_role(self, role_value: str) -> Portal | None:
        for portal in self._portals:
            if portal.role.value == role_value:
                return portal
        return None

    def _portal_loop(self, portal: Portal) -> None:
        while True:
            self._screen.clear()
            self._screen.header(portal.title, "Commands")
            choices: list[Choice | Separator] = []
            last_group = ""
            for command in portal.commands:
                if command.group and command.group != last_group:
                    choices.append(Separator(f"  {command.group}"))
                    last_group = command.group
                prefix = GROUP_PREFIX.get(command.group, " ")
                choices.append(
                    Choice(f"{prefix} {command.label}", command.key, command.description)
                )
            choices.append(Separator())
            choices.append(Choice("  Back to portals", _BACK))
            choices.append(Choice("  Exit", _EXIT))
            choice = self._prompter.choose(f"{portal.title}", choices)
            if choice is None or choice == _BACK:
                self._screen.clear()
                self._screen.banner()
                return
            if choice == _EXIT:
                self._screen.clear()
                self._screen.goodbye()
                raise SystemExit(0)
            command = portal.find(choice)
            if command is None:
                continue
            self._run_command(portal, command)

    def _collect_argument(self, argument: Argument) -> str | None:
        if argument.options:
            option_choices = [Choice(opt, opt) for opt in argument.options]
            return self._prompter.choose(argument.label, option_choices)
        for attempt in range(_MAX_ATTEMPTS):
            remaining = _MAX_ATTEMPTS - attempt - 1
            value = self._prompter.ask(argument.label, default=argument.default)
            if value is None:
                return None
            if not value.strip() and argument.default is None:
                if remaining:
                    self._screen.warning(
                        f"Cannot be blank. {remaining} attempt(s) remaining."
                    )
                else:
                    self._screen.error("Too many invalid attempts.")
                continue
            if argument.validator is not None:
                try:
                    argument.validator(value)
                except Exception as err:
                    if remaining:
                        self._screen.warning(
                            f"{err} ({remaining} attempt(s) remaining)"
                        )
                    else:
                        self._screen.error("Too many invalid attempts.")
                    continue
            return value
        return None

    def _run_command(self, portal: Portal, command) -> None:
        self._screen.clear()
        self._screen.header(portal.title, command.label)
        args: dict[str, str] = {}
        for argument in command.arguments:
            value = self._collect_argument(argument)
            if value is None:
                self._after_action()
                return
            args[argument.key] = value
        if command.confirmation is not None and not self._prompter.confirm(
            command.confirmation, default=False
        ):
            self._screen.warning("Cancelled.")
            self._after_action()
            return
        try:
            result = command.handler(args)
        except DigitalIdError as err:
            self._screen.error(f"rejected: {err}")
            self._after_action()
            return
        except ValueError as err:
            self._screen.error(str(err))
            self._after_action()
            return
        if result is not None:
            self._screen.console.print()
            self._screen.console.print(result)
            self._screen.console.print()
        self._screen.rule()
        self._after_action()

    def _after_action(self) -> None:
        if self._pause:
            self._screen.pause()
