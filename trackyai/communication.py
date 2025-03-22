import logging
from collections import deque
from typing import Any, Callable, Coroutine, Literal, Sequence

from pydantic import BaseModel
from telegram import Bot, Message, Update, User
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class _ChatTurn(BaseModel, frozen=True):
    role: Literal['user', 'agent']
    message: str | None


class TelegramChatUpdate(BaseModel, frozen=True, arbitrary_types_allowed=True):
    user: User
    message: Message


class CommunicationProxy:
    _bot: Bot | None = None
    _communication_proxies: dict[int, 'CommunicationProxy'] = {}

    def __init__(self, user_id: int):
        logger.info(f'Initializing CommunicationProxy for {user_id}')
        self._user_id = user_id
        self._message_history: deque[_ChatTurn] = deque(maxlen=6)

    @classmethod
    def setup_proxy(cls, bot: Bot):
        CommunicationProxy._bot = bot

    @classmethod
    def get_for(cls, user_id: int) -> 'CommunicationProxy':
        if user_id not in CommunicationProxy._communication_proxies:
            CommunicationProxy._communication_proxies[user_id] = CommunicationProxy(user_id=user_id)
        return CommunicationProxy._communication_proxies[user_id]

    def receive(self, update: Update, *args, **kwargs) -> TelegramChatUpdate:  # noqa: ARG002
        if update.message is None or update.effective_user is None:
            raise ValueError('Update cannot be empty')
        if update.effective_user.id != self._user_id:
            raise ValueError(
                'This communication proxy belongs to a different user. '
                f'Update: {update.effective_user.id}, Proxy: {self._user_id}'
            )
        chat_update = TelegramChatUpdate(user=update.effective_user, message=update.message)
        self._message_history.append(_ChatTurn(role='user', message=chat_update.message.text))
        return chat_update

    async def send_text(self, message: str) -> None:
        if self._bot is None:
            raise RuntimeError('Communication proxy is not initialized')
        self._message_history.append(_ChatTurn(role='agent', message=message))
        await self._bot.send_message(chat_id=self._user_id, text=message)

    @property
    def history(self) -> Sequence[_ChatTurn]:
        return tuple(self._message_history)


def comm_proxy_receive(
    func: Callable[[TelegramChatUpdate], Coroutine[Any, Any, Any]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, Any]]:
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if update.effective_user is None:
            return
        comm_proxy = CommunicationProxy.get_for(update.effective_user.id)
        chat_update = comm_proxy.receive(update, context=context)
        return await func(chat_update)

    return wrapper
