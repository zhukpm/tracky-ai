from typing import Any, Callable, Coroutine, Protocol, Self

from pydantic import BaseModel, model_validator
from telegram import Update
from telegram.ext import ContextTypes


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


class ToolResult(BaseModel, frozen=True):
    name: str
    result: Any
    success: bool = True
    exc_message: str | None = None


class ToolCall(BaseModel, frozen=True):
    name: str
    parameters: dict[str, str]


# Telegram actions as a side result for tools


class TgAction(Protocol):
    async def perform(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: ...


class SendTextMessage(TgAction):
    def __init__(self, text: str) -> None:
        self.text = text

    async def perform(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None:
            return
        await context.bot.send_message(chat_id=update.effective_user.id, text=self.text)
