"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings for API, worker, bot delivery, and observability."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="teams-card-dispatcher", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/teams_dispatcher",
        alias="DATABASE_URL",
    )

    worker_poll_interval_seconds: int = Field(
        default=5,
        alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_batch_size: int = Field(default=50, alias="WORKER_BATCH_SIZE")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")

    bot_app_id: str = Field(default="", alias="BOT_APP_ID")
    bot_app_password: SecretStr = Field(default=SecretStr(""), alias="BOT_APP_PASSWORD")
    bot_tenant_id: str = Field(default="", alias="BOT_TENANT_ID")
    teams_service_url: str = Field(
        default="",
        alias="TEAMS_SERVICE_URL",
        validation_alias=AliasChoices("TEAMS_SERVICE_URL", "BOT_SERVICE_URL"),
    )
    bot_name: str = Field(default="OpenClaw Bot", alias="BOT_NAME")

    seq_url: str | None = Field(default=None, alias="SEQ_URL")
    seq_api_key: SecretStr | None = Field(default=None, alias="SEQ_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance to avoid repeated env parsing."""

    return Settings()
