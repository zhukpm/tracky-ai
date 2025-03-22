import asyncio
import inspect
import logging
from typing import Annotated, Any, Callable, Coroutine, Iterable, Sequence, get_args, get_origin

from trackyai.agent.tools.base import Tool, ToolArgument, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class _ToolsRegistry:
    def __init__(self):
        self._available_tools: dict[str, Tool] = {}
        self._scoped_tools: dict[str, list[Tool]] = {}

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, str):
            return item in self._available_tools
        if isinstance(item, (Tool, ToolCall)):
            return item.name in self._available_tools
        if isinstance(item, ToolResult):
            return item.tool_call.name in self._available_tools
        if asyncio.iscoroutinefunction(item):
            return item.__name__ in self._available_tools
        logger.debug(f'Item not found in the registry: {item}')
        return False

    def __getitem__(self, item: Any) -> Tool:
        if item not in self:
            raise KeyError(item)
        if isinstance(item, str):
            return self._available_tools[item]
        if isinstance(item, (Tool, ToolCall)):
            return self._available_tools[item.name]
        if isinstance(item, ToolResult):
            return self._available_tools[item.tool_call.name]
        if not asyncio.iscoroutinefunction(item):
            logger.warning(f'__getitem__: Item not found in the registry: {item!r}.')
            raise ValueError(f'{item} is not a coroutine function. Why?')
        return self._available_tools[item.__name__]

    def add(self, tool: Tool) -> None:
        logger.debug(f'Adding a new tool: {tool}')
        if tool in self:
            raise ValueError(f'{tool} is already registered: {self[tool]}')
        self._available_tools[tool.name] = tool
        for scope in tool.scopes:
            self._scoped_tools.setdefault(scope, []).append(tool)

    def get(self, *scopes_or_tools: str | Tool | Callable[..., Coroutine]) -> Iterable[Tool]:
        logger.debug(f'Getting registered tools for: {scopes_or_tools}')
        if not scopes_or_tools:
            return self._available_tools.values()
        tools = set()
        for scope_or_tool in scopes_or_tools:
            if isinstance(scope_or_tool, str) and scope_or_tool in self._scoped_tools:
                tools.update(self._scoped_tools[scope_or_tool])
            else:
                tools.add(self[scope_or_tool])
        return tools


tool_registry: _ToolsRegistry = _ToolsRegistry()


def _as_supported_typename(t: Any) -> str:
    tname: str = str(t.__name__) if hasattr(t, '__name__') else str(t)
    if tname not in ('int', 'float', 'str', 'datetime', 'bool', 'list'):
        raise ValueError(f'{tname} is not a supported type')
    return tname


def tool(
    tool_function: Callable[..., Coroutine[Any, Any, Any]] | None = None,
    /,
    *,
    terminating: bool = False,
    scopes: str | Sequence[str] = 'main',
) -> (
    Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]
    | Callable[..., Coroutine[Any, Any, Any]]
):
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError('A tool must be a coroutine function')

        tool_arguments: list[ToolArgument] = []

        params = inspect.signature(func).parameters
        for param_name, param in params.items():
            if get_origin(param.annotation) is not Annotated:
                raise ValueError('Tool argument types must be Annotated')
            type_args = get_args(param.annotation)
            if not len(type_args) == 2:
                raise ValueError('Argument annotations must contain exactly 2 values: type and description')
            if not isinstance(type_args[1], str):
                raise ValueError(f'Second argument in argument annotation must be a string, {type_args=}')
            tool_arguments.append(
                ToolArgument(name=param_name, type=_as_supported_typename(type_args[0]), description=type_args[1])
            )

        functool = Tool(
            name=func.__name__,
            awaitable=func,
            description=(func.__doc__ or '') + f'\nTerminating: {terminating}.',
            arguments=tool_arguments,
            terminating=terminating,
            scopes=[scopes] if isinstance(scopes, str) else tuple(scopes),
        )

        tool_registry.add(functool)

        return func

    if tool_function is None:
        return decorator
    return decorator(tool_function)
