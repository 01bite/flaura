from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from flaura.agent.types import AgentChunk, Message, ProviderToolSchema


class AgentProvider(ABC):
    """Adapter for any AI backend (Ollama, OpenAI, Anthropic, …).

    Providers are stateless. Every call to `run()` is given the full conversation
    so far as a list of provider-neutral `Message` objects. The provider:
      1. Translates `messages` → its wire format.
      2. Translates `tools` → its wire format via `format_tools()`.
      3. Streams the model output back as `AgentChunk`s.

    The tool-use loop lives in `AgentCore`, not here, so adding a new provider
    is a single-file change with no tool-loop knowledge required.
    """

    name: str

    @abstractmethod
    def run(
        self,
        messages: list[Message],
        tools: list[ProviderToolSchema] | None = None,
    ) -> AsyncIterator[AgentChunk]:
        """Stream AgentChunks for one model turn.

        Subclasses implement as `async def` generators. Yield `text_delta` chunks
        for streamed text and `tool_use` chunks when the model requests a tool.
        End with a `done` chunk to signal the model turn is over (no more output
        from this call — AgentCore decides whether to continue the loop).
        """
        raise NotImplementedError

    def format_tools(self, schemas: list[ProviderToolSchema]) -> list[Any]:
        """Translate provider-neutral schemas to this provider's wire format."""
        return list(schemas)
