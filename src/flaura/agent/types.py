from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ChunkType = Literal["text_delta", "tool_use", "tool_result", "done"]
Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    """A single tool invocation requested by the agent."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """Provider-neutral conversation message.

    Providers translate a list[Message] to their wire format on every run().
    The shape covers the four roles every modern chat API uses, plus the
    `tool_calls` / `tool_call_id` fields needed for tool-use round trips.
    """

    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""
    tool_name: str = ""


@dataclass
class AgentChunk:
    """Single streaming event surfaced to the dispatcher / UI.

    Fields are populated based on `type`:
      text_delta  → use `text`
      tool_use    → use `tool_name`, `tool_args`, `tool_use_id`
      tool_result → use `tool_name`, `tool_use_id`, `text`, `is_error`
      done        → no payload; end of the user's turn (post tool-loop)
    """

    type: ChunkType
    text: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""
    is_error: bool = False


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
    tool_name: str
    content: Any
    is_error: bool = False
