from typing import Protocol
from unittest.mock import AsyncMock

import botocore.exceptions

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from app.core.db import get_dynamodb_client
from app.version import __version__


class MockDescribeTableFactory(Protocol):
    def __call__(self, client_error: dict | None = None) -> AsyncMock: ...


@pytest.fixture
def mock_dynamodb_client_describe_table(app: FastAPI) -> MockDescribeTableFactory:
    """Mock DynamoDB aioboto3 describe_table() method"""

    def _mock_describe_table(client_error: dict | None = None) -> AsyncMock:
        mock_client = AsyncMock()
        if client_error:
            mock_client.describe_table.side_effect = botocore.exceptions.ClientError(
                error_response={"Error": client_error},  # ty:ignore[invalid-argument-type]
                operation_name="DescribeTable",
            )

        app.dependency_overrides[get_dynamodb_client] = lambda: mock_client
        return mock_client

    return _mock_describe_table


def test_api_syntheticz_endpoint_healthy(client: TestClient):
    response = client.get("/syntheticz")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.json() == {
        "service": {"name": "service-portal-state", "version": __version__},
        "status": "UP",
        "external_systems": {"dynamodb": {"status": "UP"}},
    }


def test_api_syntheticz_endpoint_is_not_cached(client: TestClient):
    response = client.get("/syntheticz")

    assert response.headers["Cache-Control"] == "no-store"


def test_api_syntheticz_endpoint_is_idempotent(client: TestClient):
    """The check must not accumulate any state, so repeated calls give the same result."""
    first = client.get("/syntheticz")
    second = client.get("/syntheticz")

    assert first.status_code == 200
    assert first.json() == second.json()


def test_api_syntheticz_endpoint_dynamodb_down(
    client: TestClient, mock_dynamodb_client_describe_table: MockDescribeTableFactory
):
    mock_dynamodb_client_describe_table(
        client_error={"Code": "ResourceNotFoundException", "Message": "Table not found"}
    )

    response = client.get("/syntheticz")

    assert response.status_code == 500
    assert response.json() == {
        "service": {"name": "service-portal-state", "version": __version__},
        "status": "DOWN",
        "external_systems": {"dynamodb": {"status": "DOWN"}},
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_api_syntheticz_endpoint_uses_read_only_dynamodb_call(
    client: TestClient, mock_dynamodb_client_describe_table: MockDescribeTableFactory
):
    mock_client = mock_dynamodb_client_describe_table()

    client.get("/syntheticz")

    mock_client.describe_table.assert_awaited_once()
    mock_client.put_item.assert_not_awaited()
    mock_client.delete_item.assert_not_awaited()


def test_syntheticz_route_is_internal_only(client: TestClient):
    spec = client.get("openapi.json").json()
    internal_spec = client.get("internal/openapi.json").json()

    assert "/syntheticz" not in spec["paths"]
    assert "/syntheticz" in internal_spec["paths"]
