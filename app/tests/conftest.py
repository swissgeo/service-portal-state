import json
from collections.abc import Generator
from decimal import Decimal
from typing import Any, Protocol
from unittest.mock import AsyncMock

import boto3
import botocore.exceptions
from moto.server import ThreadedMotoServer
from mypy_boto3_dynamodb import DynamoDBClient
from mypy_boto3_dynamodb.service_resource import Table

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from app.core.db import get_dynamodb_client
from app.core.hashing import canonical_hash_bytes_96
from app.settings import Settings, get_settings


class MockPutItemFactory(Protocol):
    def __call__(
        self,
        return_value: dict | None = None,
        client_error: dict | None = None,
        mock_client: AsyncMock | None = None,
    ) -> AsyncMock: ...


class MockGetItemFactory(Protocol):
    def __call__(
        self,
        return_value: dict,
        mock_client: AsyncMock | None = None,
    ) -> AsyncMock: ...


@pytest.fixture
def mock_dynamodb_client_get_item(app: FastAPI) -> MockGetItemFactory:
    """Mock DynamoDB aioboto3 get_item() method"""

    def _mock_get_item(return_value: dict, mock_client: AsyncMock | None = None) -> AsyncMock:
        if mock_client is None:
            mock_client = AsyncMock()
        mock_client.get_item.return_value = return_value

        app.dependency_overrides[get_dynamodb_client] = lambda: mock_client
        return mock_client

    return _mock_get_item


@pytest.fixture
def mock_dynamodb_client_put_item(app: FastAPI) -> MockPutItemFactory:
    """Mock DynamoDB aioboto3 put_item() method"""

    def _mock_put_item(
        return_value: dict | None = None,
        client_error: dict | None = None,
        mock_client: AsyncMock | None = None,
    ) -> AsyncMock:
        if mock_client is None:
            mock_client = AsyncMock()
        mock_client.put_item.return_value = return_value
        if client_error:
            side_effect = botocore.exceptions.ClientError(
                error_response={
                    "Error": client_error,
                },  # ty:ignore[invalid-argument-type]
                operation_name="PutItem",
            )
            mock_client.put_item.side_effect = side_effect

        app.dependency_overrides[get_dynamodb_client] = lambda: mock_client
        return mock_client

    return _mock_put_item


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")


@pytest.fixture
def moto_server() -> Generator[str]:
    """Fixture to run a mocked AWS server for testing."""
    # Note: pass `port=0` to get a random free port.
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


@pytest.fixture
def settings(moto_server: str) -> Settings:
    """Fixture to provide application settings for testing, overriding the DynamoDB endpoint URL."""
    return Settings(
        # Pydantic will automatically load any .env or .env.default file, so for testing to avoid
        # any different test result between CI and local environment (in which .env file can differ)
        # we make sure pydantic doesn't load the environment file with `_env_file=None`
        _env_file=None,  # ty:ignore[unknown-argument]
        cors_origins=["http://test.com", "https://hello.com"],
        cors_origin_regex=r"http://localhost:\d+",
        aws_endpoint_url=moto_server,
        aws_dynamodb_table_name="test-table",
        aws_region="eu-central-1",
        root_path="",
        otel_sdk_disabled=True,
        publish_openapi_spec=True,
    )


@pytest.fixture
def db_client(settings: Settings) -> DynamoDBClient:
    """Fixture to provide a DynamoDB client configured to connect to the mocked AWS server."""
    return boto3.client(
        "dynamodb", endpoint_url=settings.aws_endpoint_url, region_name=settings.aws_region
    )


@pytest.fixture
def db_table(settings: Settings) -> Table:
    """
    Fixture to provide a DynamoDB Table resource connected to the mocked AWS server for testing.
    """
    dynamodb = boto3.resource(
        "dynamodb", endpoint_url=settings.aws_endpoint_url, region_name=settings.aws_region
    )
    return dynamodb.Table(settings.aws_dynamodb_table_name)


@pytest.fixture(autouse=True)
def setup_db(settings: Settings, db_client: DynamoDBClient) -> Generator[None]:
    """Fixture to set up the DynamoDB table before each test and tear it down afterward."""
    with open("dynamodb-local-config.json", encoding="utf-8") as fd:
        table_config = fd.read()
    table_config = table_config.replace(
        "${AWS_DYNAMODB_TABLE_NAME}", settings.aws_dynamodb_table_name
    )
    table_config = json.loads(table_config)

    db_client.create_table(**table_config)

    yield

    db_client.delete_table(TableName=settings.aws_dynamodb_table_name)


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """Fixture to mock the application settings for testing.

    This fixture is required for the initial application startup settings.
    Setttings dependency injection mocking is done in the `client` fixture with the settings
    fixture.
    """
    monkeypatch.setattr("app.settings.get_settings", lambda: settings)


@pytest.fixture
def app() -> FastAPI:
    """Fixture to provide the FastAPI application instance for testing.

    This is important to use it in order to have all the mocking, especially the settings mocking,
    in place before the application is initialized.
    """
    # Do the import here to ensure that the application is initialized after the settings
    # are mocked.
    from app.main import app as fastapi_app  # noqa: PLC0415

    return fastapi_app


@pytest.fixture
def client(app: FastAPI, settings: Settings) -> Generator[TestClient]:
    """Fixture to provide a TestClient for the FastAPI application with settings dependency
    injection mocked.
    """

    def get_settings_override() -> Settings:
        return settings

    with TestClient(app) as client:
        app.dependency_overrides[get_settings] = get_settings_override
        yield client


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


@pytest.fixture
def db_state_item_full(db_table: Table) -> tuple[dict, str]:
    """Fixture to insert a test state item into the DynamoDB table and return the item and state
    as json.

    The item has all fields populated, including optional ones.
    """
    item = {
        "state": {
            "layers": [
                {
                    "dimensions": {
                        "time": {
                            "currentValue": "2025-01-01T00:00:00Z",
                        },
                    },
                    "isVisible": False,
                    "layerUrl": "https://services.swissgeo.ch/api/oar/v0/collections/swissgeo.catalog/items/ch.bafu.neophyten-grossbluetiges_heusenkraut?language=de",
                    "opacity": Decimal("0.75"),
                    "type": "dataset",
                },
            ],
            "map": {
                "center": [
                    2670000,
                    1190000,
                ],
                "rotation": 2,
                "zoom": 2,
            },
        }
    }
    item_json = json.dumps(item, cls=DecimalEncoder)
    full_hash, state_id = canonical_hash_bytes_96(item_json.encode("utf-8"))
    item = item | {
        "id": state_id,
        "full_hash": full_hash,
        "major_version": 1,
        "created": "2025-01-01T00:00:00Z",
        "last_accessed": "2025-01-01T00:00:00Z",
    }

    db_table.put_item(Item=item)
    return item, item_json


@pytest.fixture
def db_state_item_empty(db_table: Table) -> tuple[dict, str]:
    """Fixture to insert an empty test state item into the DynamoDB table and return the item.

    The item has only the required fields populated, with an empty state.
    """
    item = {
        "state": {},
    }

    item_json = json.dumps(item)
    full_hash, state_id = canonical_hash_bytes_96(item_json.encode("utf-8"))
    item = item | {
        "id": state_id,
        "full_hash": full_hash,
        "major_version": 1,
        "created": "2025-01-01T00:00:00Z",
        "last_accessed": "2025-01-01T00:00:00Z",
    }
    db_table.put_item(Item=item)
    return item, item_json
