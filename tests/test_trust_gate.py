from __future__ import annotations

from pathlib import Path

from flaura.plugins.loader import (
    create_plugin_scaffold,
    discover,
    discover_user_plugins,
    load_trusted,
    trust_plugin,
    untrust_plugin,
)


def test_scaffold_creates_untrusted(tmp_path: Path):
    create_plugin_scaffold("mytools", app_home=tmp_path)
    found = discover(app_home=tmp_path)
    assert len(found) == 1
    assert found[0].name == "mytools"
    assert found[0].trusted is False

    plugins = discover_user_plugins(app_home=tmp_path)
    assert plugins == []


def test_trust_then_load(tmp_path: Path):
    create_plugin_scaffold("mytools", app_home=tmp_path)
    trust_plugin("mytools", app_home=tmp_path)

    assert "mytools" in load_trusted(app_home=tmp_path)

    plugins = discover_user_plugins(app_home=tmp_path)
    assert len(plugins) == 1
    assert plugins[0].name == "mytools"


def test_untrust_removes_from_trusted(tmp_path: Path):
    create_plugin_scaffold("mytools", app_home=tmp_path)
    trust_plugin("mytools", app_home=tmp_path)
    untrust_plugin("mytools", app_home=tmp_path)

    assert "mytools" not in load_trusted(app_home=tmp_path)
    plugins = discover_user_plugins(app_home=tmp_path)
    assert plugins == []
