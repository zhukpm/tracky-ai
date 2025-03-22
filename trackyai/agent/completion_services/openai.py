import json
import logging
from datetime import datetime
from typing import Any, Sequence

from openai import AsyncOpenAI

from trackyai.agent.chat import Chat, TextMessage
from trackyai.agent.completion_services.base import CompletionService
from trackyai.agent.tools import Tool, ToolArgument, ToolCall, ToolResult, tool_registry

# string
# number
# boolean
# null/empty
# object
# array


logger = logging.getLogger(__name__)


def _as_json_schema_type(t: str) -> str:
    match t:
        case 'int':
            return 'number'
        case 'float':
            return 'number'
        case 'str':
            return 'string'
        case 'bool':
            return 'boolean'
        case _:
            raise ValueError(f'{t} is not a valid type for OpenAI CompletionService')


def _parse_tool_input(t: str, param: Any) -> Any:
    match t:
        case 'int':
            return int(param)
        case 'float':
            return float(param)
        case 'str':
            return str(param)
        case 'bool':
            if isinstance(param, bool):
                return param
            if str(param).lower() == 'true':
                return True
            if str(param).lower() == 'false':
                return False
            raise ValueError(f'{param} is not a valid boolean')
        case 'datetime':
            return datetime.strptime(param, '%d-%m-%Y %H:%M:%S')
        case 'list':
            if isinstance(param, list):
                return param
            if isinstance(param, str):
                return json.loads(param)
            raise ValueError(f'{param} is not a valid list')
        case _:
            raise ValueError(f'{t} is not a valid type for OpenAI CompletionService')


def _make_func_property(arg: ToolArgument) -> dict:
    if arg.type == 'datetime':
        return {
            'type': 'string',
            'description': arg.description
            + '\nPass datetime as a string in the following format: %d-%m-%Y %H:%M:%S. Example: '
            + datetime(2025, 5, 30, 16, 54, 43).strftime('%d-%m-%Y %H:%M:%S'),
        }
    if arg.type == 'list':
        return {'type': 'array', 'items': {'type': 'number'}, 'description': arg.description}
    return {'type': _as_json_schema_type(arg.type), 'description': arg.description}


def _prepare_tools(tools: Sequence[Tool]) -> list[dict]:
    openai_tools = []
    for tool in tools:
        openai_tools.append(
            {
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description,
                    'parameters': {
                        'type': 'object',
                        'properties': {arg.name: _make_func_property(arg) for arg in tool.arguments},
                        'required': [arg.name for arg in tool.arguments],
                        'additionalProperties': False,
                    },
                    'strict': True,
                },
            }
        )
    return openai_tools


class OpenAI(CompletionService):
    def __init__(self, base_url: str, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=90)

    async def infer_toolcall(self, system_prompt: str, chat: Chat, tools: Sequence[Tool]) -> ToolCall:
        messages: list[dict[str, Any]] = [{'role': 'system', 'content': system_prompt}]
        for turn in chat:
            if isinstance(turn, TextMessage):
                messages.append(turn.model_dump())
            elif isinstance(turn, ToolCall):
                messages.append(
                    {
                        'role': 'assistant',
                        'tool_calls': [
                            {
                                'id': turn.id,
                                'type': 'function',
                                'function': {'name': turn.name, 'arguments': json.dumps(turn.parameters, default=str)},
                            }
                        ],
                    }
                )
            elif isinstance(turn, ToolResult):
                messages.append(
                    {
                        'role': 'tool',
                        'tool_call_id': turn.tool_call.id,
                        'content': str(turn.result) if turn.success else str(turn.exc_message),
                    }
                )

        completion = await self.client.chat.completions.create(  # type: ignore
            model='gpt-4o-mini',
            messages=messages,
            temperature=0,
            seed=11,
            tools=_prepare_tools(tools),
            tool_choice='required',
            parallel_tool_calls=False,
        )
        logger.debug(f'OpenAI completion: {completion}')

        tool_call = completion.choices[0].message.tool_calls[0]
        logger.debug(f'OpenAI tool call: {tool_call}')
        args = json.loads(tool_call.function.arguments)

        tool: Tool = tool_registry[tool_call.function.name]

        return ToolCall(
            name=tool.name,
            id=tool_call.id,
            parameters={arg.name: _parse_tool_input(arg.type, args[arg.name]) for arg in tool.arguments},
        )
