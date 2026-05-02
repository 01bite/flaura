from __future__ import annotations

from pathlib import Path


def get_history_path() -> Path:
    path = Path.home() / ".flaura" / "history.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
