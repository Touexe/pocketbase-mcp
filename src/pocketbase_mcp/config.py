"""Server configuration from environment variables."""

from __future__ import annotations

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POCKETBASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "http://127.0.0.1:8090"
    admin_email: str | None = None
    admin_password: str | None = None
    enable_destructive: bool = False
    http_host: str = Field(default="127.0.0.1", validation_alias="POCKETBASE_MCP_HOST")
    http_port: int = Field(default=8000, validation_alias="POCKETBASE_MCP_PORT")
    log_page_size_max: int = 500
    # PocketBase's own `batch.maxRequests` defaults to 50; a larger client-side
    # limit only produces an opaque server-side "Invalid batch request data".
    batch_limit: int = 50

    @computed_field  # type: ignore[prop-decorator]
    @property
    def auto_auth(self) -> bool:
        return bool(self.admin_email and self.admin_password)


settings = Settings()
