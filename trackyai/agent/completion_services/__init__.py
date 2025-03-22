from functools import cache
from typing import Literal

from trackyai.agent.completion_services.base import CompletionService
from trackyai.agent.completion_services.openai import OpenAI
from trackyai.config import settings

__all__ = ['get_completion_service', 'CompletionService']


@cache
def get_completion_service(name: Literal['openai']) -> CompletionService:
    if name != 'openai':
        raise NotImplementedError(f'{name} completion service is not implemented.')
    return OpenAI(base_url=settings.openai.base_url, api_key=settings.openai.api_key)
