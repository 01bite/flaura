from __future__ import annotations

import asyncio
import platform
import subprocess
from typing import TYPE_CHECKING

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from flaura.core.dispatcher import Dispatcher
from flaura.core.history import get_history_path
from flaura.ui.command_line import CommandCompleter
from flaura.ui.console import Console
from flaura.ui.session import ReplSession

if TYPE_CHECKING:
    from flaura.core.app import FlauraApp


def _copy_to_clipboard(text: str) -> bool:
    if not text:
        return False
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return True
        if system == "Linux":
            for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "-b", "-i"]):
                try:
                    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                    return True
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            return False
        if system == "Windows":
            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, shell=True)
            return True
    except Exception:
        return False
    return False


class Repl:
    def __init__(self, app: FlauraApp) -> None:
        self._app = app

        style = Style.from_dict(app.config.colors)
        self._console = Console(style=style)
        self._dispatcher = Dispatcher(
            console=self._console,
            registry=app.registry,
            agent=app.agent,
            knowledge=app.knowledge,
        )

        self._session = ReplSession(
            history_path=get_history_path(),
            style=style,
            get_command_completer=lambda: CommandCompleter(app, app.commands),
            on_copy_all=self._copy_all,
            on_copy_last=self._copy_last,
        )

    # ── F2 / F3 callbacks ────────────────────────────────────────────────────

    def _copy_all(self) -> None:
        ok = _copy_to_clipboard(self._dispatcher.transcript)
        self._console.info("[✔ copied transcript]" if ok else "[✗ copy failed]")

    def _copy_last(self) -> None:
        ok = _copy_to_clipboard(self._dispatcher.last_response)
        self._console.info("[✔ copied last response]" if ok else "[✗ copy failed]")

    # ── main loop ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        self._console.banner(
            provider_name=self._app.provider_name(),
            n_plugins=len(self._app.list_plugins()),
            debug=self._app.debug,
        )

        while not self._app.should_quit():
            try:
                with patch_stdout(raw=True):
                    text = await self._session.prompt()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            text = text.strip("\n")
            if not text:
                self._console.separator()
                continue

            try:
                if self._session.command_mode:
                    self._handle_command(text)
                    self._session.reset_command_mode()
                else:
                    # Re-sync agent in case set_provider changed it.
                    if self._dispatcher.agent is not self._app.agent:
                        self._dispatcher.agent = self._app.agent
                    await self._handle_chat(text)
            except KeyboardInterrupt:
                self._console.ensure_newline()
                self._console.info("[cancelled]")

            self._console.separator()

    # ── command handling ─────────────────────────────────────────────────────

    def _handle_command(self, line: str) -> None:
        try:
            result = self._app.commands.execute(self._app, line)
        except Exception as e:
            result = f"error: {e}"

        if result:
            text = result.strip()
            lowered = text.lower()
            is_error = (
                lowered.startswith("error")
                or lowered.startswith("unknown command")
                or lowered.startswith("invalid")
                or lowered.startswith("usage:")
            )
            self._console.command_result(text, is_error=is_error)

    # ── chat handling ────────────────────────────────────────────────────────

    async def _handle_chat(self, text: str) -> None:
        task = asyncio.create_task(self._dispatcher.dispatch(text))
        try:
            await task
        except asyncio.CancelledError:
            pass
