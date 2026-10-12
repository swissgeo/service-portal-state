from collections.abc import Generator
from unittest.mock import AsyncMock

import botocore.exceptions

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from app.core.db import get_dynamodb_client
from app.version import __version__


@pytest.fixture
def mock_dynamodb_client_describe_table(app: FastAPI) -> Generator[AsyncMock]:
    """Mock DynamoDB aioboto3 describe_table() method"""
    mock_client = AsyncMock()
    app.dependency_overrides[get_dynamodb_client] = lambda: mock_client
    yield mock_client
    app.dependency_overrides.pop(get_dynamodb_client, None)


def test_api_syntheticz_endpoint_up(client: TestClient):
    response = client.get("/syntheticz")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.text}"
    )
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "service": {"name": "service-portal-state", "version": __version__},
        "status": "UP",
        "external_systems": {"dynamodb": {"status": "UP"}},
    }


@pytest.mark.parametrize(
    "side_effect",
    [
        botocore.exceptions.ClientError(
            error_response={
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Requested resource not found",
                },
            },
            operation_name="DescribeTable",
        ),
        botocore.exceptions.EndpointConnectionError(endpoint_url="http://dynamodb"),
        RuntimeError("Unexpected error"),
    ],
)
def test_api_syntheticz_endpoint_down(
    client: TestClient,
    mock_dynamodb_client_describe_table: AsyncMock,
    side_effect: Exception,
):
    mock_dynamodb_client_describe_table.describe_table.side_effect = side_effect

    response = client.get("/syntheticz")

    assert response.status_code == 500, (
        f"Unexpected response {response.status_code}: {response.text}"
    )
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "service": {"name": "service-portal-state", "version": __version__},
        "status": "DOWN",
        "external_systems": {"dynamodb": {"status": "DOWN"}},
    }
    mock_dynamodb_client_describe_table.describe_table.assert_awaited_once_with(
        TableName="test-table"
    )
