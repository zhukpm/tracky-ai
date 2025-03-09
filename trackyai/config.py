from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        frozen=True,
        env_prefix='TRACKYAI_'
    )

    bot_token: str
    allowed_user_ids: frozenset[int]
