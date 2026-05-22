"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings for API, worker, Graph, and observability."""

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

    graph_tenant_id: str = Field(default="", alias="GRAPH_TENANT_ID")
    graph_client_id: str = Field(default="", alias="GRAPH_CLIENT_ID")
    graph_client_secret: SecretStr = Field(default=SecretStr(""), alias="GRAPH_CLIENT_SECRET")
    graph_scope: str = Field(default="https://graph.microsoft.com/.default", alias="GRAPH_SCOPE")
    graph_timeout_seconds: int = Field(default=20, alias="GRAPH_TIMEOUT_SECONDS")

    seq_url: str | None = Field(default=None, alias="SEQ_URL")
    seq_api_key: SecretStr | None = Field(default=None, alias="SEQ_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance to avoid repeated env parsing."""

    return Settings()
