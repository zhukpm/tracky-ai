import logging
from functools import wraps
from typing import Any, Callable, Coroutine

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from trackyai.config import settings
from trackyai.log import setup_logging

logger = logging.getLogger(__name__)


RESTRICTED_MESSAGE = """Sorry, this is a private Bot.
If you want a Tracky AI instance for yourself then take a look at https://github.com/zhukpm/tracky-ai."""


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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return
    logger.info(f'Got /start request from {update.effective_user.username} ({update.effective_user.id})')
    await context.bot.send_message(chat_id=update.effective_user.id, text="I'm a bot, please talk to me!")


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    logger.info(f'Got message from {update.effective_user.username} ({update.effective_user.id})')
    response = f'Hello, {update.effective_user.username}!\nYou said: {update.message.text}'
    await context.bot.send_message(chat_id=update.effective_user.id, text=response)


if __name__ == '__main__':
    setup_logging()

    application = ApplicationBuilder().token(settings.bot_token).build()

    start_handler = CommandHandler('start', start)
    messages_handler = MessageHandler(filters.TEXT, process_message)

    application.add_handler(start_handler)
    application.add_handler(messages_handler)

    application.run_polling()
