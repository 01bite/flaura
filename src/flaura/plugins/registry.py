from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool, ToolResult

if TYPE_CHECKING:
    from flaura.agent.types import ProviderToolSchema


class PluginRegistry:
    """Holds all registered plugins and a flat tool index for the agent."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._tools: dict[str, Tool] = {}

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"plugin {plugin.name!r} is already registered")
        for tool in plugin.get_tools():
            if tool.name in self._tools:
                owner = self._tools[tool.name].plugin_name
                raise ValueError(
                    f"tool {tool.name!r} from plugin {plugin.name!r} "
                    f"conflicts with the same-named tool from {owner!r}"
                )
        self._plugins[plugin.name] = plugin
        for tool in plugin.get_tools():
            tool.plugin_name = plugin.name
            self._tools[tool.name] = tool

    def unregister(self, plugin_name: str) -> None:
        if plugin_name not in self._plugins:
            return
        plugin = self._plugins.pop(plugin_name)
        for tool in plugin.get_tools():
            self._tools.pop(tool.name, None)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_tool_schemas(self) -> list[ProviderToolSchema]:
        """Provider-neutral schemas for the agent."""
        from flaura.agent.types import ProviderToolSchema
        return [
            ProviderToolSchema(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, args: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(content=f"unknown tool: {name}", is_error=True)

        validation_error = _validate_args(args, tool.input_schema)
        if validation_error:
            return ToolResult(
                content=f"invalid arguments for {name}: {validation_error}",
                is_error=True,
            )

        try:
            result = tool.handler(**args)
            return ToolResult(content=result, is_error=False)
        except Exception as e:
            return ToolResult(content=f"{type(e).__name__}: {e}", is_error=True)


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def _validate_args(args: Any, schema: dict[str, Any]) -> str | None:
    """Minimal JSON-schema validation for tool args. Returns error string or None."""
    if not isinstance(args, dict):
        return f"expected object, got {type(args).__name__}"

    if not isinstance(schema, dict):
        return None  # no schema to validate against

    properties = schema.get("properties") or {}
    required = schema.get("required") or []

    for key in required:
        if key not in args:
            return f"missing required field {key!r}"

    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in properties:
                return f"unexpected field {key!r}"

    for key, value in args.items():
        prop_schema = properties.get(key)
        if not isinstance(prop_schema, dict):
            continue
        expected = prop_schema.get("type")
        if expected is None:
            continue
        types = expected if isinstance(expected, list) else [expected]
        allowed: tuple[type, ...] = tuple(t for typ in types for t in _JSON_TYPES.get(typ, ()))
        if not allowed:
            continue
        # bool is a subclass of int — exclude it from numeric checks.
        if isinstance(value, bool) and bool not in allowed:
            return f"field {key!r} expected {expected}, got bool"
        if not isinstance(value, allowed):
            return f"field {key!r} expected {expected}, got {type(value).__name__}"
    return None
