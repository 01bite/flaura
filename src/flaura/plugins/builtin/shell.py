from __future__ import annotations

import subprocess

from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool


def _run_shell(command: str, cwd: str | None = None, timeout: int = 30) -> dict:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


class ShellPlugin(Plugin):
    name = "shell"
    description = "Run shell commands and capture their output."

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="run_shell",
                description="Run a shell command. Returns exit_code, stdout, stderr.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string", "description": "working directory (optional)"},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["command"],
                },
                handler=_run_shell,
            ),
        ]
