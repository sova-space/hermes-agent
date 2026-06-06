"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config comes from env vars. Required fields fail loud at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"

    openrouter_api_key: str
    doer_model: str = "anthropic/claude-sonnet-4-5"

    github_token: str
    github_api_url: str = "https://api.github.com"

    doer_bot_token: str
    telegram_chat_id: int = -1003913424869
    telegram_projects_topic_id: int = 167


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
