from __future__ import annotations

from abc import ABC, abstractmethod

from flaura.plugins.types import Tool


class Plugin(ABC):
    """A plugin packages one or more tools the agent can call.

    All registered plugins are loaded simultaneously. The agent decides which
    tools to use based on its reasoning — there is no "active" plugin concept.
    Plugins are toolboxes, not modes.
    """

    name: str
    description: str

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return the tools this plugin exposes."""
        ...

    def extract_knowledge(self, tool_result: str) -> tuple[list[dict], list[dict]]:
        """Extract knowledge from a tool result. Return (nodes, edges) patch."""
        return [], []
