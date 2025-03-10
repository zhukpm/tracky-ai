import logging
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        frozen=True,
        env_prefix='TRACKYAI_'
    )

    bot_token: str
    allowed_user_ids: frozenset[int]

    log_dir: str = '/var/log'
    log_level: int | str = logging.INFO

    @field_validator('log_level')
    @classmethod
    def validate_log_levels(cls, log_level: int | str) -> int:
        try:
            log_level = int(log_level)
        except ValueError:
            pass
        if isinstance(log_level, str):
            log_level = log_level.upper()
            if log_level not in logging.getLevelNamesMapping():
                raise ValueError(f'Invalid log level: {log_level}')
            return logging.getLevelNamesMapping()[log_level]
        if log_level not in logging.getLevelNamesMapping().values():
            raise ValueError(f'Invalid log level: {log_level}')
        return log_level

    def model_post_init(self, __context: Any) -> None:
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
