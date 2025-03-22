import logging
from functools import wraps
from typing import Any, Callable, Coroutine

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from trackyai.communication import CommunicationProxy, TelegramChatUpdate, comm_proxy_receive
from trackyai.config import settings
from trackyai.log import setup_logging
from trackyai.session import session_manager

logger = logging.getLogger(__name__)


RESTRICTED_MESSAGE = """Sorry, this is a private Bot.
If you want a Tracky AI instance for yourself then take a look at https://github.com/zhukpm/tracky-ai."""

START_MESSAGE = """Hi!
I'm Tracky AI - smart expenses tracker with (almost) unlimited analytics features!
Talk to me 😊
"""


async def send_restricted(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=user_id, text=RESTRICTED_MESSAGE)


def restricted(
    handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, Any]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, Any]]:
    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user is None or update.message is None:
            logger.warning('Got an Update without effective_user or message')
            return
        user_id = update.effective_user.id
        if user_id not in settings.allowed_user_ids:
            logger.warning(f'Unauthorized user {update.effective_user.username} ({user_id}): {update.message.text}')
            await send_restricted(user_id, context)
            return
        return await handler(update, context)

    return wrapped


@restricted
@comm_proxy_receive
async def start(update: TelegramChatUpdate) -> None:
    logger.info(f'Got /start request from {update.user.username} ({update.user.id})')
    await CommunicationProxy.get_for(user_id=update.user.id).send_text(message=START_MESSAGE)


@restricted
@comm_proxy_receive
async def process_message(update: TelegramChatUpdate) -> None:
    logger.info(f'Got message from {update.user.username} ({update.user.id})')
    session = session_manager.get_or_create_session(user_id=update.user.id)
    session.add_user_message(message=update.message.text or '')


def run() -> None:
    setup_logging()

    application: Application = ApplicationBuilder().token(settings.bot_token).build()
    CommunicationProxy.setup_proxy(bot=application.bot)

    start_handler = CommandHandler('start', start)
    messages_handler = MessageHandler(filters.TEXT, process_message)

    application.add_handler(start_handler)
    application.add_handler(messages_handler)

    application.run_polling()


if __name__ == '__main__':
    run()
