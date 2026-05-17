"""ANSI-coloured terminal output for the REPL.

All printing goes through prompt_toolkit's `print_formatted_text` so the active
style (from FlauraConfig.colors) controls colours, and prompt_toolkit's
`patch_stdout` (in repl.py) keeps prints from clobbering the live prompt.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import time
from pathlib import Path

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import BaseStyle

_SPINNER_CHARS = "·•●•"
_SPINNER_TICK_S = 0.12
_ANSI_CLEAR_LINE = "\r\033[2K"
_ANSI_CYAN = "\033[36m"
_ANSI_DIM = "\033[2m"
_ANSI_RESET = "\033[0m"


class Spinner:
    """Animated inline progress indicator: `[·•●] message (Ns)`.

    Writes to a single terminal line, updating in place via CR + ANSI erase.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._message = "thinking"
        self._started_at = 0.0
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self, message: str = "thinking") -> None:
        if self._task is not None and not self._task.done():
            return
        self._message = message
        self._started_at = time.monotonic()
        self._active = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._active = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None
        sys.stdout.write(_ANSI_CLEAR_LINE)
        sys.stdout.flush()

    async def _run(self) -> None:
        i = 0
        try:
            while self._active:
                elapsed = time.monotonic() - self._started_at
                char = _SPINNER_CHARS[i % len(_SPINNER_CHARS)]
                line = (
                    f"{_ANSI_CLEAR_LINE}"
                    f"{_ANSI_CYAN}[{char}]{_ANSI_RESET}"
                    f" {_ANSI_DIM}{self._message} ({elapsed:.0f}s){_ANSI_RESET}"
                )
                sys.stdout.write(line)
                sys.stdout.flush()
                await asyncio.sleep(_SPINNER_TICK_S)
                i += 1
        except asyncio.CancelledError:
            pass


def _cols() -> int:
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def _home_relative_cwd() -> str:
    try:
        cwd = Path.cwd()
        home = Path.home()
        rel = cwd.relative_to(home)
        return f"~/{rel}" if str(rel) != "." else "~"
    except (ValueError, OSError):
        try:
            return str(Path.cwd())
        except Exception:
            return ""


class Console:
    def __init__(self, style: BaseStyle | None = None) -> None:
        self._style = style
        self._line_dirty = False  # tracks whether last write ended with newline

    # ── primitives ───────────────────────────────────────────────────────────

    def print(self, *parts: tuple[str, str], end: str = "\n") -> None:
        text = FormattedText(list(parts))
        print_formatted_text(text, style=self._style, end=end, flush=True)
        self._line_dirty = not end.endswith("\n")

    def write_raw(self, text: str) -> None:
        """Stream raw text (no styling, no newline). For per-chunk streaming."""
        sys.stdout.write(text)
        sys.stdout.flush()
        self._line_dirty = not text.endswith("\n")

    def ensure_newline(self) -> None:
        if self._line_dirty:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._line_dirty = False

    # ── high-level helpers ───────────────────────────────────────────────────

    def banner(self, provider_name: str, n_plugins: int, debug: bool = False) -> None:
        pad = "  "
        debug_part: list[tuple[str, str]] = []
        if debug:
            debug_part = [("class:header.debug", "  [DEBUG]")]
        plugin_part = f"  ·  {n_plugins} plugins" if n_plugins else ""

        provider_label = provider_name or "—"
        if "/" in provider_label:
            prov, _, model = provider_label.partition("/")
            provider_parts: list[tuple[str, str]] = [
                ("class:header.provider", prov),
                ("class:header.dim", "  ·  "),
                ("class:header.provider", model),
            ]
        else:
            provider_parts = [("class:header.provider", provider_label)]

        self.print(("class:header.pad", pad), ("class:header.title", "Flaura"), *debug_part)
        self.print(
            ("class:header.pad", pad),
            *provider_parts,
            ("class:header.dim", plugin_part),
        )
        self.print(
            ("class:header.pad", pad),
            ("class:header.cwd", _home_relative_cwd()),
        )
        self.print(("", ""))
        self.separator()

    def separator(self) -> None:
        self.print(("class:output.separator", "─" * _cols()))

    def assistant_prefix(self) -> None:
        self.print(("class:output.assistant-mark", "⏺ "), end="")

    def assistant_chunk(self, text: str) -> None:
        self.write_raw(text)

    def timing(self, elapsed_s: float, threshold_s: float = 1.0) -> None:
        if elapsed_s < threshold_s:
            return
        self.print(("", ""))
        self.print(("class:output.timing", f"✔ Churned for {_format_elapsed(elapsed_s)}"))

    def command_result(self, text: str, is_error: bool) -> None:
        if not text:
            return
        first, *rest = text.split("\n")
        marker = "✗" if is_error else "✔"
        cls = "class:output.error" if is_error else "class:output.success"
        self.print((cls, f"[{marker} {first}]"))
        for line in rest:
            self.print(("", line))

    def tool_use(self, name: str, args) -> None:
        self.print(("class:output.tool-use", f"[tool_use: {name}] {args}"))

    def tool_result(self, name: str, text: str, is_error: bool) -> None:
        marker = "tool_error" if is_error else "tool_result"
        cls = "class:output.tool-error" if is_error else "class:output.tool-result"
        self.print((cls, f"[{marker}: {name}] {text}"))

    def error(self, text: str) -> None:
        self.print(("class:output.error", f"[✗ {text}]"))

    def info(self, text: str) -> None:
        self.print(("class:output.timing", text))

    def code_block(self, text: str, lang: str = "") -> None:
        """Pygments-highlighted code block, fences included."""
        try:
            from pygments import highlight
            from pygments.formatters import Terminal256Formatter
            from pygments.lexers import get_lexer_by_name, guess_lexer
            from pygments.util import ClassNotFound

            lexer = None
            if lang:
                try:
                    lexer = get_lexer_by_name(lang.lower())
                except ClassNotFound:
                    lexer = None
            if lexer is None:
                try:
                    lexer = guess_lexer(text)
                except Exception:
                    lexer = None

            self.print(("class:output.code-fence", f"```{lang}"))
            if lexer is None:
                self.print(("class:output.code", text.rstrip("\n")))
            else:
                rendered = highlight(text, lexer, Terminal256Formatter(style="monokai"))
                self.write_raw(rendered.rstrip("\n"))
                self.write_raw("\n")
            self.print(("class:output.code-fence", "```"))
        except Exception:
            self.print(("class:output.code-fence", f"```{lang}"))
            self.print(("class:output.code", text.rstrip("\n")))
            self.print(("class:output.code-fence", "```"))


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s" if seconds >= 1 else f"{seconds * 1000:.0f}ms"
    minutes = int(seconds // 60)
    rest = int(seconds % 60)
    return f"{minutes}m{rest}s"
