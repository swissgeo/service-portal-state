from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # NOTE: The following settings are automatically read from environment variables (environment
    # variable uses CONSTANT_CASE) and are parsed using json syntax.
    cors_origins: list[str] = Field(default=["*"], description="List of allowed origins in CORS")
    cors_method: list[str] = Field(default=["*"], description="List of allowed methods in CORS")
    cors_headers: list[str] = Field(default=["*"], description="List of allowed headers in CORS")
    cors_max_age: PositiveInt = Field(default=600, description="CORS max age")


settings = Settings()
