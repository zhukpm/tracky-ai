from typing import Literal

from pydantic import BaseModel

from trackyai.agent.tools import ToolCall, ToolResult

__all__ = ['TextMessage', 'Chat']


class TextMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class Chat:
    def __init__(self):
        self._conversation: list[TextMessage | ToolCall | ToolResult] = []

    def add_user_message(self, text: str) -> None:
        is_last_user = (
            self._conversation
            and isinstance(self._conversation[-1], TextMessage)
            and self._conversation[-1].role == 'user'
        )
        if is_last_user:
            assert isinstance(self._conversation[-1], TextMessage)
            self._conversation[-1].content += '\n' + text
        else:
            self._conversation.append(TextMessage(role='user', content=text))

    def add_agent_message(self, text: str) -> None:
        is_last_agent = (
            self._conversation
            and isinstance(self._conversation[-1], TextMessage)
            and self._conversation[-1].role == 'assistant'
        )
        if is_last_agent:
            assert isinstance(self._conversation[-1], TextMessage)
            self._conversation[-1].content += '\n' + text
        else:
            self._conversation.append(TextMessage(role='assistant', content=text))

    def add_tool_call(self, tool_call: ToolCall) -> None:
        self._conversation.append(tool_call)

    def add_tool_result(self, tool_result: ToolResult) -> None:
        self._conversation.append(tool_result)

    def __iter__(self):
        return iter(self._conversation)

    def __repr__(self):
        return repr(self._conversation)
