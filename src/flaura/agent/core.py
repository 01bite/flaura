from __future__ import annotations

from collections.abc import AsyncIterator

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, ProviderToolSchema


class AgentCore:
    """Orchestrates one agent turn through whichever provider is configured."""

    def __init__(self, provider: AgentProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> AgentProvider:
        return self._provider

    async def run(
        self,
        user_input: str,
        context: str = "",
        tools: list[ProviderToolSchema] | None = None,
    ) -> AsyncIterator[AgentChunk]:
        async for chunk in self._provider.run(
            user_input=user_input,
            context=context,
            tools=tools,
            system="",
        ):
            yield chunk
