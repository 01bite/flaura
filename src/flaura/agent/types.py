from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ChunkType = Literal["text_delta", "tool_use", "done"]


@dataclass
class AgentChunk:
    """Single streaming event from an agent provider.

    Fields are populated based on `type`:
      text_delta → use `text`
      tool_use   → use `tool_name`, `tool_args`, `tool_use_id`
      done       → no payload; signals end of turn
    """

    type: ChunkType
    text: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""


@dataclass
class ProviderToolSchema:
    """Provider-neutral tool description. Each provider translates this to its wire format."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ProviderToolResult:
    """Provider-neutral tool result, sent back to the agent after a tool_use."""

    tool_use_id: str
    content: Any
    is_error: bool = False
