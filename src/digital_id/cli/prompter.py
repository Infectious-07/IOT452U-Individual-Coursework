from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Choice:
    label: str
    value: str
    description: str = ""


class Prompter(Protocol):
    def choose(self, title: str, choices: Sequence[Choice]) -> str | None: ...
    def ask(self, message: str, default: str | None = None) -> str | None: ...
    def confirm(self, message: str, default: bool = False) -> bool: ...


class QuestionaryPrompter:
    # production backend; uses arrow key menus and styled prompts
    def choose(self, title: str, choices: Sequence[Choice]) -> str | None:
        import questionary

        question_choices = [
            questionary.Choice(title=choice.label, value=choice.value)
            for choice in choices
        ]
        return questionary.select(title, choices=question_choices).ask()

    def ask(self, message: str, default: str | None = None) -> str | None:
        import questionary

        return questionary.text(message, default=default or "").ask()

    def confirm(self, message: str, default: bool = False) -> bool:
        import questionary

        result = questionary.confirm(message, default=default).ask()
        return bool(result)


@dataclass
class ScriptedPrompter:
    # test backend; pops scripted answers in order
    answers: list

    def __init__(self, answers: Sequence) -> None:
        self.answers = list(answers)

    def _pop(self):
        if not self.answers:
            raise AssertionError("ScriptedPrompter ran out of answers")
        return self.answers.pop(0)

    def choose(self, _title: str, _choices: Sequence[Choice]) -> str | None:
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
