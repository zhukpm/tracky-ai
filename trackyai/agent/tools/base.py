from typing import Any, Callable, Coroutine, Protocol, Self, runtime_checkable

from pydantic import BaseModel, model_validator

from trackyai.communication import CommunicationProxy


class ToolArgument(BaseModel, frozen=True):
    name: str
    type: str
    description: str


class Tool(BaseModel, frozen=True):
    name: str
    awaitable: Callable[..., Coroutine[Any, Any, Any]]
    description: str
    arguments: list[ToolArgument]
    terminating: bool
    scopes: tuple[str, ...]

    def __hash__(self) -> int:
        return hash(self.name)

    @model_validator(mode='after')
    def verify_scopes(self) -> Self:
        if not self.scopes:
            raise ValueError('At least one scope must be specified')
        return self

    def is_terminating(self) -> bool:
        return self.terminating

    def is_ask_user(self) -> bool:
        return self.name == 'ask_user'


class ToolCall(BaseModel, frozen=True):
    name: str
    id: str
    parameters: dict[str, Any]


class ToolResult(BaseModel, frozen=True):
    tool_call: ToolCall
    result: Any
    success: bool = True
    exc_message: str | None = None


# Telegram actions as a side result for tools


@runtime_checkable
class TgAction(Protocol):
    async def perform(self, user_id: int) -> None: ...


class SendTextMessage(TgAction):
    def __init__(self, text: str) -> None:
        self.text = text

    async def perform(self, user_id: int) -> None:
        await CommunicationProxy.get_for(user_id=user_id).send_text(message=self.text)
