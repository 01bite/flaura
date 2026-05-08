from __future__ import annotations

import os
from pathlib import Path

from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool


def _mkdir(path: str) -> str:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return f"created {p}"


def _list_dir(path: str = ".") -> list[str]:
    p = Path(path).expanduser()
    return sorted(os.listdir(p))


def _read_file(path: str) -> str:
    return Path(path).expanduser().read_text()


def _write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} chars to {p}"


def _delete_file(path: str) -> str:
    p = Path(path).expanduser()
    p.unlink()
    return f"deleted {p}"


class FileOpsPlugin(Plugin):
    name = "fileops"
    description = "Read, write, list, and delete files; create directories."

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="mkdir",
                description="Create a directory (and any missing parents).",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                handler=_mkdir,
            ),
            Tool(
                name="list_dir",
                description="List the contents of a directory.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                    },
                },
                handler=_list_dir,
            ),
            Tool(
                name="read_file",
                description="Read the contents of a text file.",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                handler=_read_file,
            ),
            Tool(
                name="write_file",
                description="Write text content to a file (creates parents if needed).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                handler=_write_file,
            ),
            Tool(
                name="delete_file",
                description="Delete a file.",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                handler=_delete_file,
            ),
        ]
