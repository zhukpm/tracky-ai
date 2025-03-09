import logging
from functools import wraps

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

from trackyai.config import Settings

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

settings = Settings()


RESTRICTED_MESSAGE = """Sorry, this is a private Bot.
If you want a Tracky AI instance for yourself then take a look at https://github.com/zhukpm/tracky-ai."""


async def send_restricted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=RESTRICTED_MESSAGE)


def restricted(handler):
    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in settings.allowed_user_ids:
            logger.warning(f'Unauthorized user {update.effective_user.username} ({user_id}): {update.message.text}')
            await send_restricted(update, context)
            return
        return await handler(update, context, *args, **kwargs)
    return wrapped


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'Got /start request from {update.effective_user.username} ({update.effective_user.id})')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'Got message from {update.effective_user.username} ({update.effective_user.id})')
    response = f'Hello, {update.effective_user.username}!\nYou said: {update.message.text}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


if __name__ == '__main__':
    application = ApplicationBuilder().token(settings.bot_token).build()

    start_handler = CommandHandler('start', start)
    messages_handler = MessageHandler(filters.TEXT, process_message)

    application.add_handler(start_handler)
    application.add_handler(messages_handler)

    application.run_polling()
