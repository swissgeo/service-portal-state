from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.default"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # NOTE: The following settings are automatically read from environment variables (environment
    # variable uses CONSTANT_CASE) and are parsed using json syntax.

    root_path: str = "/api/state"

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_method: list[str] = ["*"]
    cors_headers: list[str] = ["*"]
    cors_max_age: int = 600

    # AWS Settings
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url: str | None = None
    aws_dynamodb_table_name: str
    aws_region: str


# Settings are wrapped in an lru_cache to ensure a single, lazily-initialized instance
# per process. This avoids re-parsing environment variables on every call, improves
# performance, and ensures consistent configuration across the application while still
# working cleanly with FastAPI dependency injection.
@lru_cache
def get_settings() -> Settings:
    return Settings()  # ty: ignore[missing-argument] for production we don't pass parameter we use environment variable
