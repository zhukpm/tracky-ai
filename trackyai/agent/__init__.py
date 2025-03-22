import logging
from functools import cache
from pathlib import Path
from typing import Iterable, Sequence

from jinja2 import Environment, FileSystemLoader, Template

from trackyai.agent.chat import Chat, TextMessage
from trackyai.agent.completion_services import CompletionService, get_completion_service
from trackyai.agent.tools import (
    SendTextMessage,
    TgAction,
    Tool,
    ToolArgument,
    ToolCall,
    ToolResult,
    tool,
    tool_registry,
)

logger = logging.getLogger(__name__)

_jinja_env = Environment(loader=FileSystemLoader(searchpath=Path(__file__).parent / 'prompt_templates'))


__all__ = [
    'Agent',
    'load_system_prompt_template',
    'TextMessage',
    'Chat',
    'get_completion_service',
    'CompletionService',
    'Tool',
    'ToolArgument',
    'ToolCall',
    'ToolResult',
    'TgAction',
    'SendTextMessage',
    'tool_registry',
    'tool',
]


@cache
def load_system_prompt_template(template_name: str) -> Template:
    logger.info(f'Loading system prompt template "{template_name}"')
    return _jinja_env.get_template(template_name + '.jinja2')


class Agent:
    def __init__(self, system_prompt: str, tools: Iterable[Tool], completion_service: CompletionService):
        self._system_prompt = system_prompt
        self._tools: Sequence[Tool] = list(tools)
        self._completion_service = completion_service

    async def think(self, chat: Chat) -> ToolCall:
        return await self._completion_service.infer_toolcall(
            system_prompt=self._system_prompt, chat=chat, tools=self._tools
        )
