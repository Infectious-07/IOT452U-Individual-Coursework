from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Choice:
    label: str
    value: str
    description: str = ""


@dataclass(frozen=True)
class Separator:
    text: str = ""


class Prompter(Protocol):
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
