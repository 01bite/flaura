from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from flaura.agent.types import AgentChunk, ProviderToolResult, ProviderToolSchema


class AgentProvider(ABC):
    """Adapter for any AI backend (Anthropic, OpenAI, Ollama, …)."""

    name: str

    @abstractmethod
    def run(
        self,
        user_input: str,
        context: str = "",
        tools: list[ProviderToolSchema] | None = None,
        system: str = "",
    ) -> AsyncIterator[AgentChunk]:
        """Stream AgentChunks for one turn. Subclasses implement as async generators."""
        raise NotImplementedError

    def format_tools(self, schemas: list[ProviderToolSchema]) -> list[Any]:
        """Translate provider-neutral schemas to this provider's wire format."""
        return list(schemas)

    def format_tool_result(self, tool_name: str, result: ProviderToolResult) -> Any:
        """Translate a tool result to this provider's wire format."""
        return result

    async def send_tool_result(self, formatted: Any) -> None:
        """Send a tool result back to the provider mid-turn (Phase 9 will use this)."""
        pass
