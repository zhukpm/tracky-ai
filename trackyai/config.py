import logging
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _PostgresDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, frozen=True, env_prefix='POSTGRES_')

    user: str
    password: str
    db: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, frozen=True, env_prefix='TRACKYAI_')

    # telegram
    bot_token: str
    allowed_user_ids: frozenset[int]

    # postgres
    pg_host: str
    pg_port: int
    pg_db: Annotated[_PostgresDatabaseSettings, Field(default_factory=_PostgresDatabaseSettings)]

    # logging & debug
    debug_mode: bool = False
    log_dir: str = '/var/log'
    log_level: int | str = logging.INFO

    @computed_field  # type: ignore[misc]
    @cached_property
    def db_uri(self) -> str:
        return f'postgresql+asyncpg://{self.pg_db.user}:{self.pg_db.password}@{self.pg_host}:{self.pg_port}/{self.pg_db.db}'

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
