from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, DynamicCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import BaseStyle


class ReplSession:
    """ptpython-style prompt.

    - Single-line mode (default): Enter submits.  Prompt is green `❯ `.
    - Multi-line mode (Esc toggles): Enter inserts a newline; M-Enter submits.
      Prompt is orange `❯ `.
    - Command mode (`:` on empty buffer): prompt is `: `; Backspace exits.
    """

    def __init__(
        self,
        history_path,
        style: BaseStyle,
        get_command_completer: Callable[[], Completer | None],
        on_copy_all: Callable[[], None] = lambda: None,
        on_copy_last: Callable[[], None] = lambda: None,
    ) -> None:
        self._command_mode = False
        self._multi = False
        self._on_copy_all = on_copy_all
        self._on_copy_last = on_copy_last

        kb = self._build_key_bindings()

        def _completer() -> Completer | None:
            return get_command_completer() if self._command_mode else None

        def _prompt() -> FormattedText:
            if self._command_mode:
                return FormattedText([("class:command-prompt", ": ")])
            cls = "class:prompt.multi" if self._multi else "class:prompt"
            return FormattedText([(cls, "❯ ")])

        def _continuation(width: int, line_number: int, is_soft_wrap: bool):
            return FormattedText([("class:prompt.dots", ". ".rjust(width))])

        self._session: PromptSession = PromptSession(
            message=_prompt,
            multiline=Condition(lambda: self._multi),
            history=FileHistory(str(history_path)),
            completer=DynamicCompleter(_completer),
            complete_while_typing=False,
            prompt_continuation=_continuation,
            style=style,
            key_bindings=kb,
            mouse_support=False,
            enable_history_search=True,
        )

    # ── state ────────────────────────────────────────────────────────────────

    @property
    def command_mode(self) -> bool:
        return self._command_mode

    @property
    def multi(self) -> bool:
        return self._multi

    def reset_command_mode(self) -> None:
        self._command_mode = False

    # ── input ────────────────────────────────────────────────────────────────

    async def prompt(self) -> str:
        return await self._session.prompt_async()

    # ── key bindings ─────────────────────────────────────────────────────────

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()
        buf = lambda: self._session.default_buffer  # noqa: E731

        # M-Enter (Alt-Enter) always submits — escape hatch in multi mode.
        @kb.add("escape", "enter")
        def _meta_enter_submit(event) -> None:
            event.current_buffer.validate_and_handle()

        # Bare Esc toggles multi-line mode (non-eager so arrow-key escape
        # sequences and M-Enter still work correctly).
        @kb.add("escape", filter=Condition(lambda: not self._command_mode))
        def _toggle_multi(event) -> None:
            self._multi = not self._multi

        # `:` at the start of an empty buffer flips into command mode.
        @kb.add(
            ":",
            filter=Condition(lambda: not self._command_mode and len(buf().text) == 0),
        )
        def _enter_command(event) -> None:
            self._command_mode = True

        # Backspace on an empty command buffer exits command mode.
        @kb.add(
            "backspace",
            filter=Condition(lambda: self._command_mode and len(buf().text) == 0),
        )
        def _exit_command(event) -> None:
            self._command_mode = False

        @kb.add("f2")
        def _copy_all(event) -> None:
            self._on_copy_all()

        @kb.add("f3")
        def _copy_last(event) -> None:
            self._on_copy_last()

        return kb
