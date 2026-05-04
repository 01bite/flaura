from __future__ import annotations

from abc import ABC

from prompt_toolkit.completion import Completer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer, SimpleLexer

from flaura.ui.prompt_style import DefaultPrompt, PromptStyle


class PromptPlugin(ABC):
    name: str

    def get_lexer(self) -> Lexer:
        return SimpleLexer()

    def get_completer(self) -> Completer | None:
        return None

    def get_prompt_style(self) -> PromptStyle:
        return DefaultPrompt()

    def get_key_bindings(self) -> KeyBindings:
        return KeyBindings()

    def is_multiline(self, text: str) -> bool:
        return False

    def on_submit(self, text: str) -> None:
        pass

    def get_title(self) -> str:
        return self.name
