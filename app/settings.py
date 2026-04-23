from functools import lru_cache
from typing import Annotated

from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi import Depends
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.default"),
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )

    # NOTE: The following settings are automatically read from environment variables (environment
    # variable uses CONSTANT_CASE) and are parsed using json syntax.

    root_path: str = ""

    # CORS settings
    cors_origins: list[str] = ["localhost"]
    cors_method: list[str] = ["GET", "POST"]
    cors_headers: list[str] = ["*"]
    cors_max_age: int = 600

    # AWS Settings
    aws_endpoint_url: str | None = None
    aws_dynamodb_table_name: str
    aws_region: str

    # In order to support dotenv file with string list directly loaded by pydantic-settings or
    # by docker run --env-file, we MUST set the list as comma separated string in the .env file
    # or environment variable, e.g. CORS_ORIGINS=test.com,localhost and then use a field validator
    # to parse it into a list of strings. Otherwise either pydantic-settings or docker will not
    # parse the list
    # correctly because each system handle quoting differently:
    # - docker would require => CORS_ORIGINS=["*"] (with quotes) to parse it as a list,
    # - pydantic-settings would require => CORS_ORIGINS='["*"]'
    @field_validator("cors_origins", "cors_method", "cors_headers", mode="before")
    @classmethod
    def parse_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        return v.split(",")


# Settings are wrapped in an lru_cache to ensure a single, lazily-initialized instance
# per process. This avoids re-parsing environment variables on every call, improves
# performance, and ensures consistent configuration across the application while still
# working cleanly with FastAPI dependency injection.
@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()  # ty: ignore[missing-argument] for production we don't pass parameter we use environment variable


SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]
