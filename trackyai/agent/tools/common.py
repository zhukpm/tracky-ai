from typing import Annotated

from trackyai.agent.tools.base import SendTextMessage
from trackyai.agent.tools.registry import tool


@tool(terminating=True, scopes='memory')
async def finish() -> None:
    """Finish the current session without doing anything else."""
    pass


@tool
async def ask_user(
    message: Annotated[str, 'A text message (usually a question) to be sent to the user in chat'],
) -> SendTextMessage:
    """
    Ask the user with a message, and await for their reply to continue the current session.
    It is used to ask for clarifications or additional information from the user if their request cannot be completed.
    """
    return SendTextMessage(message)


@tool(terminating=True)
async def finish_session_with_reply(
    message: Annotated[str, 'A final text message to be sent to the user in chat'],
) -> SendTextMessage:
    """
    Send a message to the user, and finish the current session.
    It is used when other tools are not applicable, or the user intent is unrelated to system features.
    For example, when a user asks about system capabilities, or asks general questions.
    """
    return SendTextMessage(message)
