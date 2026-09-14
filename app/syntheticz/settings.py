from pydantic_settings import BaseSettings, SettingsConfigDict


class SyntheticzSettings(BaseSettings):
    """Settings of the synthetic check plugin.

    Read from environment variables (CONSTANT_CASE), so that the plugin can be reused by any
    service without code change.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.default"),
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )

    # Name reported in the `service.name` field of the response body.
    service_name: str = "unknown-service"
    # Version reported in the `service.version` field of the response body. When left unset the
    # version passed to setup_syntheticz() is used.
    service_version: str | None = None
