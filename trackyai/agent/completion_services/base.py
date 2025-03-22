from typing import Protocol, Sequence

from trackyai.agent.chat import Chat
from trackyai.agent.tools import Tool, ToolCall


class CompletionService(Protocol):
    async def infer_toolcall(self, system_prompt: str, chat: Chat, tools: Sequence[Tool]) -> ToolCall: ...
