from unittest.mock import AsyncMock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import pytest

from app.core.db import get_dynamodb_client


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("DELETE", "/"),
        ("PUT", "/"),
        ("HEAD", "/"),
        ("DELETE", "/abcdef1234567891"),
        ("POST", "/abcdef1234567891"),
        ("PUT", "/abcdef1234567891"),
    ],
)
def test_method_not_allowed(client: TestClient, method: str, path: str):
    response = client.request(method, path)

    assert response.status_code == 405
    assert response.headers["content-type"] == "application/json"


def test_http_exception_400(app: FastAPI):
    mock_db_client = AsyncMock()
    mock_db_client.get_item.side_effect = HTTPException(400, detail={"test": "message"})
    app.dependency_overrides[get_dynamodb_client] = lambda: mock_db_client

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/abcdef1234567891")

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"error": "Bad Request", "message": "{'test': 'message'}"}


def test_exception_500(app: FastAPI):
    mock_db_client = AsyncMock()
    mock_db_client.get_item.side_effect = Exception()
    app.dependency_overrides[get_dynamodb_client] = lambda: mock_db_client

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/abcdef1234567891")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "detail": None,
        "error": "internal service error",
        "message": "An unexpected error occurred",
    }
