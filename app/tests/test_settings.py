from pydantic import ValidationError

import pytest

from app.settings import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    settings = Settings()  # ty:ignore[missing-argument]

    assert settings.root_path == "/api/wps/v1/state"
    assert settings.cors_origins == ["localhost"]
    assert settings.cors_method == ["GET", "POST"]
    assert settings.cors_headers == ["*"]
    assert settings.cors_max_age == 600


def test_env_overrides_simple_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_DYNAMODB_TABLE_NAME", "my-table")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("ROOT_PATH", "/api")

    settings = Settings()  # ty:ignore[missing-argument]

    assert settings.root_path == "/api"
    assert settings.aws_dynamodb_table_name == "my-table"
    assert settings.aws_region == "us-east-1"


def test_parse_list_from_comma_separated_string(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("CORS_ORIGINS", "example.com,localhost")
    monkeypatch.setenv("CORS_METHOD", "GET,POST,PUT")
    monkeypatch.setenv("CORS_HEADERS", "Authorization,Content-Type")

    settings = Settings()  # ty:ignore[missing-argument]

    assert settings.cors_origins == ["example.com", "localhost"]
    assert settings.cors_method == ["GET", "POST", "PUT"]
    assert settings.cors_headers == ["Authorization", "Content-Type"]


def test_parse_list_when_already_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    settings = Settings(
        cors_origins=["a.com", "b.com"],
        cors_method=["GET"],
        cors_headers=["X-Test"],
    )  # ty:ignore[missing-argument]

    assert settings.cors_origins == ["a.com", "b.com"]
    assert settings.cors_method == ["GET"]
    assert settings.cors_headers == ["X-Test"]


def test_missing_required_fields(monkeypatch: pytest.MonkeyPatch):
    # Ensure required env vars are NOT present
    monkeypatch.delenv("AWS_DYNAMODB_TABLE_NAME", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # ty:ignore[missing-argument, unknown-argument]
