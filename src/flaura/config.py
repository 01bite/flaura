from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── default style tokens (prompt_toolkit class names → style strings) ────────

DEFAULT_COLORS: dict[str, str] = {
    "status-bar":                              "bg:#444444 #ffffff bold",
    "status-bar.vi":                           "bg:#444444 #ff8800 bold",
    "status-bar.thinking":                     "bg:#444444 #00ddff bold",
    "separator":                               "bg:#333333 #555555",
    "prompt":                                  "#00aa00 bold",
    "prompt.dots":                             "#555555",
    "command-prompt":                          "#ffaa00 bold",
    "mode.multi":                              "bg:#333333 #666666",
    "mode.normal":                             "bg:#50fa7b #000000",
    "completion-menu":                         "bg:#2d2d2d #ffffff",
    "completion-menu.completion":              "bg:#2d2d2d #ffffff",
    "completion-menu.completion.current":      "bg:#00aa00 #000000 bold",
    "completion-menu.meta.completion":         "bg:#222222 #888888",
    "completion-menu.meta.completion.current": "bg:#007700 #ffffff",
    "scrollbar.background":                    "bg:#1a1a1a",
    "scrollbar.button":                        "bg:#555555",
    "search":                                  "bg:#440044 #ffffff",
    "search.current":                          "bg:#aa00aa #ffffff bold",
    "search-toolbar":                          "bg:#222222 #ffaa00",
}

# ── default config.toml written to APP_HOME on first run ─────────────────────

_DEFAULT_CONFIG_TOML = """\
# flaura configuration
# See https://github.com/your/flaura for documentation.

[app]
# Provider used at startup.  Options: "echo", "ollama"
provider = "echo"

[providers.ollama]
# Talks to a local Ollama server.  Leave model empty to use the first running model.
# model = ""
host = "http://localhost:11434"

[ui]
vi_mode = false

[ui.colors]
# Override any prompt_toolkit style token.  Keys are CSS-like class names;
# values are prompt_toolkit style strings ("bg:#rrggbb #rrggbb [bold] [italic]").
# Uncomment and edit any entry to customise colours.
#
# "status-bar"                              = "bg:#444444 #ffffff bold"
# "status-bar.vi"                           = "bg:#444444 #ff8800 bold"
# "status-bar.thinking"                     = "bg:#444444 #00ddff bold"
# "separator"                               = "bg:#333333 #555555"
# "prompt"                                  = "#00aa00 bold"
# "prompt.dots"                             = "#555555"
# "command-prompt"                          = "#ffaa00 bold"
# "mode.multi"                              = "bg:#333333 #666666"
# "mode.normal"                             = "bg:#50fa7b #000000"
# "completion-menu"                         = "bg:#2d2d2d #ffffff"
# "completion-menu.completion"              = "bg:#2d2d2d #ffffff"
# "completion-menu.completion.current"      = "bg:#00aa00 #000000 bold"
# "completion-menu.meta.completion"         = "bg:#222222 #888888"
# "completion-menu.meta.completion.current" = "bg:#007700 #ffffff"
# "scrollbar.background"                    = "bg:#1a1a1a"
# "scrollbar.button"                        = "bg:#555555"
# "search"                                  = "bg:#440044 #ffffff"
# "search.current"                          = "bg:#aa00aa #ffffff bold"
# "search-toolbar"                          = "bg:#222222 #ffaa00"
"""


@dataclass
class FlauraConfig:
    # ── paths ────────────────────────────────────────────────────────────────
    app_home: Path = field(default_factory=lambda: Path.home() / ".flaura")
    config_file: Path | None = None  # resolved in __post_init__ if None

    # ── app ──────────────────────────────────────────────────────────────────
    provider: str = "echo"

    # ── providers.ollama ─────────────────────────────────────────────────────
    ollama_model: str = ""
    ollama_host: str = "http://localhost:11434"

    # ── ui ───────────────────────────────────────────────────────────────────
    vi_mode: bool = False
    colors: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLORS))

    def __post_init__(self) -> None:
        if self.config_file is None:
            self.config_file = self.app_home / "config.toml"

    # ── factory ──────────────────────────────────────────────────────────────

    @classmethod
    def load(
        cls,
        app_home: Path | None = None,
        config_file: Path | None = None,
    ) -> FlauraConfig:
        """Build config with precedence: CLI args > env vars > config file > defaults."""

        # 1. Resolve app_home
        if app_home is None:
            raw = os.environ.get("FLAURA_HOME")
            app_home = Path(raw).expanduser() if raw else Path.home() / ".flaura"

        cfg = cls(app_home=app_home)

        # 2. Resolve config file path
        cfg.config_file = config_file if config_file is not None else app_home / "config.toml"

        # 3. Ensure app_home exists, write default config if absent
        app_home.mkdir(parents=True, exist_ok=True)
        if not cfg.config_file.exists():
            cfg.config_file.write_text(_DEFAULT_CONFIG_TOML, encoding="utf-8")

        # 4. Parse TOML
        data: dict[str, Any] = {}
        try:
            with cfg.config_file.open("rb") as fh:
                data = tomllib.load(fh)
        except Exception as e:
            sys.stderr.write(f"[flaura] config parse error ({cfg.config_file}): {e}\n")

        # 5. Merge sections
        _apply_app(cfg, data.get("app", {}))
        providers = data.get("providers", {})
        _apply_ollama(cfg, providers.get("ollama", {}))
        _apply_ui(cfg, data.get("ui", {}))

        return cfg


# ── section appliers ─────────────────────────────────────────────────────────

def _apply_app(cfg: FlauraConfig, section: dict[str, Any]) -> None:
    if "provider" in section:
        cfg.provider = str(section["provider"])


def _apply_ollama(cfg: FlauraConfig, section: dict[str, Any]) -> None:
    if "model" in section:
        cfg.ollama_model = str(section["model"])
    if "host" in section:
        cfg.ollama_host = str(section["host"])


def _apply_ui(cfg: FlauraConfig, section: dict[str, Any]) -> None:
    if "vi_mode" in section:
        cfg.vi_mode = bool(section["vi_mode"])
    # [ui.colors] is a sub-table inside the ui section after tomllib parsing
    colors = section.get("colors", {})
    if isinstance(colors, dict):
        cfg.colors.update({str(k): str(v) for k, v in colors.items()})
