from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .models import (
    Argument,
    AuditEvent,
    DigitalID,
    DigitalIdError,
    IdentityStatus,
    OrganisationRole,
    Portal,
)
from .services import Snapshot

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
    answers: list

    def __init__(self, answers: Sequence) -> None:
        self.answers = list(answers)

    def _pop(self):
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


# --- render helpers ---


def _codes(codes: frozenset) -> str:
    return ", ".join(sorted(code.value for code in codes)) or "-"


def _detail_table(title: str) -> Table:
    table = Table(
        title=f"[bold]{title}[/]",
        show_header=False,
        box=box.ROUNDED,
        border_style=BORDER_DIM,
        title_style=ACCENT,
        padding=(0, 1),
    )
    table.add_column("field", style=ACCENT2, no_wrap=True, min_width=22)
    table.add_column("value")
    return table


def _list_table(title: str) -> Table:
    return Table(
        title=f"[bold]{title}[/]",
        box=box.ROUNDED,
        border_style=BORDER_DIM,
        title_style=ACCENT,
        header_style=ACCENT,
        row_styles=["", MUTED],
        padding=(0, 1),
    )


# --- render functions ---


def identity_panel(identity: DigitalID) -> Table:
    table = _detail_table(f"Digital ID  {identity.id}")
    table.add_row("name", identity.name)
    table.add_row("dob", identity.dob.isoformat())
    table.add_row("nationality", identity.nationality)
    table.add_row("postcode", identity.postcode)
    table.add_row(
        "status",
        f"[{colour_status(identity.status)}]{identity.status.value}[/]",
    )
    table.add_row("tax reference", identity.tax_reference or "-")
    table.add_row("tax band", identity.tax_band.value if identity.tax_band else "-")
    table.add_row("driving entitlements", _codes(identity.driving_entitlements))
    table.add_row("driving restrictions", _codes(identity.driving_restrictions))
    table.add_row("right to work", "yes" if identity.right_to_work else "no")
    table.add_row("residency", identity.residency_status.value)
    table.add_row("updated at", identity.updated_at.isoformat(timespec="seconds"))
    return table


def identity_list_table(identities: Sequence[DigitalID]) -> Table:
    table = _list_table("Digital IDs")
    table.add_column("id", style=BORDER)
    table.add_column("name")
    table.add_column("status")
    table.add_column("nationality")
    table.add_column("tax band")
    table.add_column("right to work")
    for identity in identities:
        table.add_row(
            identity.id,
            identity.name,
            f"[{colour_status(identity.status)}]{identity.status.value}[/]",
            identity.nationality,
            identity.tax_band.value if identity.tax_band else "-",
            "yes" if identity.right_to_work else "no",
        )
    return table


def audit_table(events: Sequence[AuditEvent], title: str = "Audit events") -> Table:
    table = _list_table(title)
    table.add_column("occurred at", style=BORDER)
    table.add_column("actor")
    table.add_column("action", style="bold")
    table.add_column("identity")
    table.add_column("payload", style=MUTED)
    for event in events:
        table.add_row(
            event.occurred_at.isoformat(timespec="seconds"),
            event.actor_role,
            event.action.value,
            event.identity_id or "-",
            str(dict(event.payload)),
        )
    return table


def stats_table(snapshot: Snapshot) -> Table:
    table = _detail_table("System snapshot")
    table.add_row("total identities", str(snapshot.total))
    for status, count in snapshot.by_status.items():
        table.add_row(f"  {status.lower()}", str(count))
    table.add_row("events in last 7 days", str(snapshot.events_last_7_days))
    return table


def tax_response_table(response) -> Table:
    table = _detail_table(f"Tax check  {response.identity_id}")
    table.add_row("exists", "yes" if response.exists else "no")
    table.add_row("active now", "yes" if response.active_now else "no")
    table.add_row(
        "suspended in period",
        "[bold red]yes[/]" if response.suspended_in_period else "no",
    )
    table.add_row(
        "period",
        f"{response.period_start.isoformat()} .. {response.period_end.isoformat()}",
    )
    table.add_row("tax reference", response.tax_reference or "-")
    table.add_row(
        "tax band", response.tax_band.value if response.tax_band else "-"
    )
    return table


def dvla_response_table(response) -> Table:
    table = _detail_table(f"DVLA check  {response.identity_id}")
    table.add_row("exists", "yes" if response.exists else "no")
    table.add_row(
        "active now",
        "[bold green]yes[/]" if response.active_now else "[red]no[/]",
    )
    table.add_row(
        "restricted now",
        "[bold red]yes[/]" if response.restricted_now else "no",
    )
    table.add_row("entitlements", _codes(response.entitlements))
    table.add_row("restrictions", _codes(response.restrictions))
    return table


def employer_response_table(response) -> Table:
    table = _detail_table(f"Employer check  {response.identity_id}")
    table.add_row(
        "valid now",
        "[bold green]yes[/]" if response.valid_now else "[red]no[/]",
    )
    table.add_row("right to work", "yes" if response.right_to_work else "no")
    return table


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
