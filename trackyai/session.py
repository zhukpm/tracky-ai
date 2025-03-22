import asyncio
import datetime
import logging
from typing import Any, Coroutine

from trackyai.agent import Agent, load_system_prompt_template
from trackyai.agent.chat import Chat
from trackyai.agent.completion_services import get_completion_service
from trackyai.agent.tools import TgAction, ToolCall, ToolResult, tool_registry
from trackyai.communication import CommunicationProxy
from trackyai.db import service_manager

logger = logging.getLogger(__name__)


_async_tasks = set()


def ensure_async_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _async_tasks.add(task)
    task.add_done_callback(_async_tasks.remove)
    return task


class Session:
    def __init__(self, user_id: int) -> None:
        self._user_id: int = user_id
        self._chat: Chat | None = None
        self._agent: Agent | None = None
        self._user_messages: list[str] = []
        self._need_processing = asyncio.Event()
        self._process: asyncio.Task | None = None

    def done(self) -> bool:
        return self._process is not None and self._process.done()

    def add_user_message(self, message: str) -> None:
        if self.done():
            raise ValueError('Cannot add a user message to a finished session')
        self._need_processing.set()
        self._user_messages.append(message)

    async def _process_session(self):
        logger.debug('Starting processing session. Awaiting for session updates...')
        await self._need_processing.wait()
        logger.debug('Got an update in the session. Executing processing pipeline.')

        if self._user_messages:
            self._chat.add_user_message('\n'.join(self._user_messages))
            self._user_messages.clear()
        self._need_processing.clear()

        decision: ToolCall = await self._agent.think(self._chat)

        while self._need_processing.is_set() or decision not in tool_registry:
            logger.debug(f'Got a new message, or made a bad decision - retrying thinking for {self._user_id}')
            if self._user_messages:
                self._chat.add_user_message('\n'.join(self._user_messages))
                self._user_messages.clear()
                self._need_processing.clear()
            decision = await self._agent.think(self._chat)

        if tool_registry[decision].is_terminating():
            logger.info(f'Terminating session for user {self._user_id}; calling {decision.name}')
            ensure_async_task(self._make_toolcall(decision))
            return

        if tool_registry[decision].is_ask_user():
            logger.info(f'Asking user {self._user_id} for additional info.')
            self._chat.add_agent_message(
                decision.parameters.get(
                    tool_registry[decision].arguments[0].name, 'message was not generated in ask_user'
                )
            )
            await self._make_toolcall(decision)
            self._process = asyncio.create_task(self._process_session())
            return

        logger.info(f'Performing a non-terminating tool call {decision.name} for user {self._user_id}.')
        self._chat.add_tool_call(decision)
        tool_result: ToolResult = await self._make_toolcall(decision)
        self._chat.add_tool_result(tool_result)
        self._need_processing.set()
        self._process = asyncio.create_task(self._process_session())

    async def _make_toolcall(self, tool_call: ToolCall) -> ToolResult:
        logger.info(f'Calling tool {tool_call.name} with args {tool_call.parameters}...')
        tool = tool_registry[tool_call.name]

        try:
            result = await tool.awaitable(**tool_call.parameters)
        except BaseException as e:
            logger.error(f'Error while calling a tool {tool_call}.', exc_info=e)
            return ToolResult(tool_call=tool_call, result=None, success=False, exc_message=repr(e))

        if isinstance(result, TgAction):
            try:
                await result.perform(user_id=self._user_id)
                return ToolResult(tool_call=tool_call, result=None, success=True)
            except BaseException as e:
                logger.error(
                    f'Error while executing a telegram action from the tool {tool_call.name}. Tool call: {tool_call}.',
                    exc_info=e,
                )
                return ToolResult(tool_call=tool_call, result=None, success=False, exc_message=repr(e))

        return ToolResult(tool_call=tool_call, result=result, success=True)

    async def init(self) -> None:
        logger.info(f'Initializing session for {self._user_id}...')
        system_prompt_template = load_system_prompt_template('main')
        ecs = await service_manager.env_config.get_all()
        categories = await service_manager.category.get_all()
        latest_expenses = await service_manager.expense.latest(5)
        memory = await service_manager.memory.get(self._user_id)
        now = datetime.datetime.now(tz=datetime.UTC)
        self._chat = Chat()
        self._agent = Agent(
            system_prompt=system_prompt_template.render(
                ecs=ecs,
                categories=categories,
                latest_expenses=latest_expenses,
                latest_dialog=CommunicationProxy.get_for(self._user_id).history,
                memory=memory.memory,
                current_dt_full=now.strftime('%A, %B %d, %Y %H:%M'),
            ),
            tools=tool_registry.get('main'),
            completion_service=get_completion_service('openai'),
        )
        self._process = asyncio.create_task(self._process_session())


class SessionsManager:
    def __init__(self):
        self.sessions: dict[int, Session] = {}

    def get_or_create_session(self, user_id: int) -> Session:
        session = self.sessions.get(user_id)
        if not session or session.done():
            logger.info(f'Creating new session for user {user_id}')
            session = Session(user_id=user_id)
            self.sessions[user_id] = session
            ensure_async_task(session.init())
        return session


session_manager = SessionsManager()
