from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from models import (
    Argument,
    Command,
    DigitalIdError,
    OrganisationRole,
    Portal,
)
from render import (
    ACCENT,
    ACCENT2,
    BANNER,
    BORDER,
    BORDER_DIM,
    ERROR,
    HEADER_STYLE,
    MUTED,
    SUCCESS,
    WARNING,
)

# --- prompter ---


@dataclass(frozen=True)
class Choice:
    label: str
    value: str
    description: str = ""


@dataclass(frozen=True)
class Separator:
    text: str = ""


class Prompter(Protocol):  # pragma: no cover
    def choose(self, title: str, choices: Sequence[Choice | Separator]) -> str | None: ...
    def choose_many(self, title: str, choices: Sequence[Choice]) -> list[str] | None: ...
    def ask(self, message: str, default: str | None = None) -> str | None: ...
    def confirm(self, message: str, default: bool = False) -> bool: ...


class QuestionaryPrompter:  # pragma: no cover
    def choose(self, title: str, choices: Sequence[Choice | Separator]) -> str | None:
        import questionary
        from prompt_toolkit.styles import Style

        style = Style.from_dict({
            "question": "bold",
            "answer": "fg:ansicyan bold",
            "pointer": "fg:ansicyan bold",
            "highlighted": "fg:ansicyan bold underline",
            "selected": "fg:ansigreen bold",
            "separator": "fg:ansiblue bold",
            "instruction": "fg:ansigray italic",
        })
        question_choices = []
        for item in choices:
            if isinstance(item, Separator):
                question_choices.append(questionary.Separator(item.text))
            else:
                question_choices.append(
                    questionary.Choice(title=item.label, value=item.value)
                )
        return questionary.select(
            title,
            choices=question_choices,
            style=style,
            pointer="▶",
            instruction="(arrow keys to navigate, enter to select)",
        ).ask()

    def choose_many(self, title: str, choices: Sequence[Choice]) -> list[str] | None:
        import questionary
        from prompt_toolkit.styles import Style

        style = Style.from_dict({
            "question": "bold",
            "answer": "fg:ansicyan bold",
            "pointer": "fg:ansicyan bold",
            "highlighted": "fg:ansicyan bold underline",
            "selected": "fg:ansigreen bold",
            "instruction": "fg:ansigray italic",
        })
        question_choices = [
            questionary.Choice(title=item.label, value=item.value)
            for item in choices
        ]
        return questionary.checkbox(
            title,
            choices=question_choices,
            style=style,
            pointer="▶",
            instruction="(space to toggle, enter to confirm)",
        ).ask()

    def ask(self, message: str, default: str | None = None) -> str | None:
        import questionary

        return questionary.text(message, default=default or "").ask()

    def confirm(self, message: str, default: bool = False) -> bool:
        import questionary

        result = questionary.confirm(message, default=default).ask()
        return bool(result)


@dataclass
class ScriptedPrompter:
    """Test double for `Prompter` that returns answers from a pre-populated list."""

    answers: list

    def __init__(self, answers: Sequence[object]) -> None:
        self.answers = list(answers)

    def _pop(self) -> object:
        if not self.answers:
            raise AssertionError("ScriptedPrompter ran out of answers")
        return self.answers.pop(0)

    def choose(self, _title: str, _choices: Sequence[Choice | Separator]) -> str | None:
        return self._pop()

    def choose_many(self, _title: str, _choices: Sequence[Choice]) -> list[str] | None:
        return self._pop()

    def ask(self, _message: str, default: str | None = None) -> str | None:
        value = self._pop()
        if value is None:
            return default
        return value

    def confirm(self, _message: str, default: bool = False) -> bool:
        value = self._pop()
        if value is None:
            return default
        return bool(value)


# --- screen ---


class Screen:
    """Thin wrapper over `rich.Console` that paints the banner, headers and status messages."""

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


# --- menu shell ---


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
    """Interactive REPL that drives portal and command selection via a Prompter."""

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
        if argument.options and argument.multi_select:
            option_choices = [Choice(opt, opt) for opt in argument.options]
            selected = self._prompter.choose_many(argument.label, option_choices)
            if selected is None:
                return None
            return ",".join(selected)
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

    def _run_command(self, portal: Portal, command: Command) -> None:
        self._screen.clear()
        self._screen.header(portal.title, command.label)
        try:
            args = self._collect_arguments(command)
            if args is None:
                return
            if not self._confirm_if_needed(command):
                return
            self._dispatch(command, args)
        finally:
            self._after_action()

    def _collect_arguments(self, command: Command) -> dict[str, str] | None:
        args: dict[str, str] = {}
        for argument in command.arguments:
            value = self._collect_argument(argument)
            if value is None:
                return None
            args[argument.key] = value
        return args

    def _confirm_if_needed(self, command: Command) -> bool:
        if command.confirmation is None:
            return True
        if self._prompter.confirm(command.confirmation, default=False):
            return True
        self._screen.warning("Cancelled.")
        return False

    def _dispatch(self, command: Command, args: dict[str, str]) -> None:
        try:
            result = command.handler(args)
        except DigitalIdError as err:
            self._screen.error(f"rejected: {err}")
            return
        except ValueError as err:
            self._screen.error(str(err))
            return
        if result is not None:
            self._screen.console.print()
            self._screen.console.print(result)
            self._screen.console.print()
        self._screen.rule()

    def _after_action(self) -> None:
        if self._pause:
            self._screen.pause()
