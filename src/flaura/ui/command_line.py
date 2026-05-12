from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

from flaura.core.commands import _PROVIDERS

if TYPE_CHECKING:
    from flaura.core.app import FlauraApp
    from flaura.core.commands import CommandRegistry


# Cache (host -> (models, expires_at)) so repeated tab presses don't re-fetch.
_OLLAMA_CACHE_TTL = 5.0
_ollama_cache: dict[str, tuple[list[str], float]] = {}


def _fetch_ollama_models(host: str) -> list[str]:
    cached = _ollama_cache.get(host)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]

    models: list[str] = []
    try:
        import ollama
        response = ollama.Client(host=host).list()
        models = [m.model for m in response.models if m.model]
    except Exception:
        pass

    _ollama_cache[host] = (models, now + _OLLAMA_CACHE_TTL)
    return models


class CommandCompleter(Completer):
    """Live completions for `:command [args...]` syntax."""

    def __init__(self, app: FlauraApp, commands: CommandRegistry) -> None:
        self._app = app
        self._commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split(" ")

        # First token: command name
        if len(parts) == 1:
            prefix = parts[0]
            for name in self._commands.names():
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
            return

        cmd = parts[0]
        rest = parts[-1]  # last token = what we're currently completing

        if cmd == "plugin" and len(parts) == 2:
            for sub in ("install", "remove", "create"):
                if sub.startswith(rest):
                    yield Completion(sub, start_position=-len(rest))

        elif cmd == "plugin" and len(parts) == 3 and parts[1] == "remove":
            for p in self._app.list_plugins():
                if p.name.startswith(rest):
                    yield Completion(p.name, start_position=-len(rest))

        elif cmd == "provider" and len(parts) == 2:
            # If the user has already typed a complete provider that takes a
            # model arg (e.g. "provider ollama"), jump straight to model
            # completions — insert " <model>" after the cursor so the
            # resulting text is "provider ollama <model>".
            if rest == "ollama":
                for m in _fetch_ollama_models(self._app.ollama_host()):
                    yield Completion(" " + m, start_position=0, display=m)
            else:
                for p in _PROVIDERS:
                    if p.startswith(rest):
                        yield Completion(p, start_position=-len(rest))

        elif cmd == "provider" and len(parts) == 3 and parts[1] == "ollama":
            for m in _fetch_ollama_models(self._app.ollama_host()):
                if m.startswith(rest):
                    yield Completion(m, start_position=-len(rest))

        elif cmd == "tool" and len(parts) == 2:
            for t in self._app.list_tools():
                if t.name.startswith(rest):
                    yield Completion(
                        t.name,
                        start_position=-len(rest),
                        display_meta=t.description,
                    )
