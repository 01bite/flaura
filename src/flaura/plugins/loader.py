"""Loads user-installed plugins from ~/.flaura/plugins/.

Each plugin lives in its own directory:
    ~/.flaura/plugins/<name>/
        plugin.toml   — metadata: name, description, entry_point ("module:Class")
        plugin.py     — Plugin subclass
        requirements.txt  (optional)

`:plugin install <git-url>` (future) clones a repo into this directory.
"""
from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

from flaura.plugins.base import Plugin


def user_plugins_dir() -> Path:
    p = Path.home() / ".flaura" / "plugins"
    p.mkdir(parents=True, exist_ok=True)
    return p


def discover_user_plugins() -> list[Plugin]:
    """Walk ~/.flaura/plugins/ and instantiate every Plugin subclass found."""
    plugins: list[Plugin] = []
    root = user_plugins_dir()

    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        try:
            plugin = _load_plugin_from_dir(entry)
            if plugin is not None:
                plugins.append(plugin)
        except Exception as e:
            sys.stderr.write(f"[flaura] failed to load plugin {entry.name}: {e}\n")

    return plugins


def _load_plugin_from_dir(path: Path) -> Plugin | None:
    toml_path = path / "plugin.toml"
    py_path = path / "plugin.py"

    if not toml_path.exists() or not py_path.exists():
        return None

    with toml_path.open("rb") as f:
        meta = tomllib.load(f)

    class_name = meta.get("entry_point", "").split(":", 1)[-1] or None

    spec = importlib.util.spec_from_file_location(
        f"flaura_user_plugins.{path.name}", py_path
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if class_name and hasattr(module, class_name):
        cls = getattr(module, class_name)
    else:
        # Auto-detect: first Plugin subclass in module
        cls = None
        for attr in vars(module).values():
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                cls = attr
                break
        if cls is None:
            return None

    return cls()
