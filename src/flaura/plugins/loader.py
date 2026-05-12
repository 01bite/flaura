"""Loads user-installed plugins from ~/.flaura/plugins/.

Each plugin lives in its own directory:
    ~/.flaura/plugins/<name>/
        plugin.toml   — metadata: name, description, entry_point ("module:Class")
        plugin.py     — Plugin subclass
        requirements.txt  (optional)

Trust gate: user plugins run as full Python in this process. Discovered
plugins are NOT loaded until the user trusts them with `:plugin trust <name>`,
which persists to `<app_home>/plugins/.trusted.json`.

`:plugin install <git-url>` (future) clones a repo into this directory.
`:plugin create <name>` scaffolds a new plugin folder with a working template.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from flaura.plugins.base import Plugin

_PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_TRUSTED_FILE = ".trusted.json"


@dataclass
class DiscoveredPlugin:
    """A plugin directory found on disk, possibly not yet trusted."""

    name: str
    path: Path
    description: str
    trusted: bool


def user_plugins_dir(app_home: Path | None = None) -> Path:
    base = app_home if app_home is not None else Path.home() / ".flaura"
    p = base / "plugins"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _trusted_path(app_home: Path | None = None) -> Path:
    return user_plugins_dir(app_home) / _TRUSTED_FILE


def load_trusted(app_home: Path | None = None) -> set[str]:
    """Return the set of plugin names the user has explicitly trusted."""
    path = _trusted_path(app_home)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"[flaura] could not read {path}: {e}\n")
        return set()
    if isinstance(data, dict):
        names = data.get("trusted") or []
    elif isinstance(data, list):
        names = data
    else:
        names = []
    return {str(n) for n in names if isinstance(n, str)}


def save_trusted(names: set[str], app_home: Path | None = None) -> None:
    path = _trusted_path(app_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps({"trusted": sorted(names)}, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def trust_plugin(name: str, app_home: Path | None = None) -> None:
    if not _PLUGIN_NAME_RE.match(name):
        raise ValueError(f"invalid plugin name: {name!r}")
    plugin_dir = user_plugins_dir(app_home) / name
    if not plugin_dir.is_dir():
        raise ValueError(f"no such plugin directory: {plugin_dir}")
    trusted = load_trusted(app_home)
    trusted.add(name)
    save_trusted(trusted, app_home)


def untrust_plugin(name: str, app_home: Path | None = None) -> None:
    trusted = load_trusted(app_home)
    trusted.discard(name)
    save_trusted(trusted, app_home)


def discover(app_home: Path | None = None) -> list[DiscoveredPlugin]:
    """List every plugin directory on disk, with its trust status."""
    root = user_plugins_dir(app_home)
    trusted = load_trusted(app_home)
    found: list[DiscoveredPlugin] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        toml_path = entry / "plugin.toml"
        description = ""
        if toml_path.exists():
            try:
                with toml_path.open("rb") as f:
                    meta = tomllib.load(f)
                description = str(meta.get("description") or "")
            except Exception:
                pass
        found.append(
            DiscoveredPlugin(
                name=entry.name,
                path=entry,
                description=description,
                trusted=entry.name in trusted,
            )
        )
    return found


def discover_user_plugins(app_home: Path | None = None) -> list[Plugin]:
    """Walk <app_home>/plugins/ and instantiate every TRUSTED Plugin subclass.

    Untrusted plugins are skipped silently here; the application surfaces a
    notice to the user separately via `discover()`.
    """
    plugins: list[Plugin] = []
    trusted_names = load_trusted(app_home)
    untrusted: list[str] = []

    for found in discover(app_home):
        if found.name not in trusted_names:
            untrusted.append(found.name)
            continue
        try:
            plugin = _load_plugin_from_dir(found.path)
            if plugin is not None:
                plugins.append(plugin)
        except Exception as e:
            sys.stderr.write(f"[flaura] failed to load plugin {found.name}: {e}\n")

    if untrusted:
        sys.stderr.write(
            f"[flaura] {len(untrusted)} untrusted plugin(s) skipped: "
            f"{', '.join(untrusted)}. Run `:plugin trust <name>` to enable.\n"
        )

    return plugins


def _load_plugin_from_dir(path: Path) -> Plugin | None:
    toml_path = path / "plugin.toml"
    py_path = path / "plugin.py"

    if not toml_path.exists() or not py_path.exists():
        return None

    with toml_path.open("rb") as f:
        meta = tomllib.load(f)

    class_name = meta.get("entry_point", "").split(":", 1)[-1] or None

    spec = importlib.util.spec_from_file_location(f"flaura_user_plugins.{path.name}", py_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if class_name and hasattr(module, class_name):
        cls = getattr(module, class_name)
    else:
        cls = None
        for attr in vars(module).values():
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                cls = attr
                break
        if cls is None:
            return None

    return cls()


# ── scaffolding ──────────────────────────────────────────────────────────────

_PLUGIN_TOML_TEMPLATE = """\
name = "{name}"
description = "{description}"
entry_point = "plugin:{class_name}"
"""

_PLUGIN_PY_TEMPLATE = '''\
"""{name} plugin for flaura.

Edit the tools below — each one becomes a function the agent can call.
The `input_schema` is a JSON-schema dict that flaura validates before
calling your handler.
"""

from __future__ import annotations

from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool


def _hello(name: str = "world") -> str:
    return f"hello, {{name}}!"


def _add(a: float, b: float) -> float:
    return a + b


class {class_name}(Plugin):
    name = "{name}"
    description = "{description}"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="{name}_hello",
                description="Greet someone by name.",
                input_schema={{
                    "type": "object",
                    "properties": {{
                        "name": {{"type": "string", "description": "Who to greet."}},
                    }},
                    "additionalProperties": False,
                }},
                handler=_hello,
            ),
            Tool(
                name="{name}_add",
                description="Add two numbers.",
                input_schema={{
                    "type": "object",
                    "properties": {{
                        "a": {{"type": "number"}},
                        "b": {{"type": "number"}},
                    }},
                    "required": ["a", "b"],
                    "additionalProperties": False,
                }},
                handler=_add,
            ),
        ]
'''


def create_plugin_scaffold(name: str, app_home: Path | None = None) -> Path:
    """Create a new plugin directory with a working template.

    Returns the path to the created plugin directory.
    Raises ValueError on invalid name or if the directory already exists.
    """
    if not _PLUGIN_NAME_RE.match(name):
        raise ValueError(
            f"invalid plugin name {name!r}: must be lowercase letters, "
            f"digits, and underscores; must start with a letter"
        )

    root = user_plugins_dir(app_home)
    plugin_dir = root / name
    if plugin_dir.exists():
        raise ValueError(f"plugin directory already exists: {plugin_dir}")

    class_name = "".join(part.capitalize() for part in name.split("_")) + "Plugin"
    description = f"{name} plugin"

    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.toml").write_text(
        _PLUGIN_TOML_TEMPLATE.format(
            name=name, description=description, class_name=class_name
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        _PLUGIN_PY_TEMPLATE.format(
            name=name, description=description, class_name=class_name
        ),
        encoding="utf-8",
    )
    return plugin_dir
