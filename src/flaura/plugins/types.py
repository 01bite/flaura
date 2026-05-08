from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    """A single capability the agent can invoke."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]
    plugin_name: str = ""  # filled in by the registry on register


@dataclass
class ToolResult:
    """Result of running a tool."""

    content: Any
    is_error: bool = False
