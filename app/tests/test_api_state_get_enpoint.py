from fastapi.testclient import TestClient

import pytest


def test_get_app_full_state(client: TestClient, db_state_item_full: dict):
    state_id = db_state_item_full[0]["id"]

    response = client.get(f"/{state_id}")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    assert data == {
        "state": db_state_item_full[0]["state"],
    }


def test_get_app_empty_state(client: TestClient, db_state_item_empty: dict):
    state_id = db_state_item_empty[0]["id"]

    response = client.get(f"/{state_id}")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    assert data == {"state": {}}


@pytest.mark.parametrize(
    ("origin", "method"),
    [("http://test.com", "GET"), ("http://localhost", "POST"), ("https://hello.com", "POST")],
)
def test_cors_allow_origin_header(
    client: TestClient, db_state_item_empty: dict, origin: str, method: str
):
    state_id = db_state_item_empty[0]["id"]
    response = client.options(
        f"/{state_id}",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
        },
    )

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.text}"
    )
    assert response.headers["access-control-allow-origin"] == origin

    response = client.get(
        f"/{state_id}",
        headers={
            "Origin": origin,
        },
    )

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.text}"
    )


@pytest.mark.parametrize(
    ("origin", "method"),
    [
        ("https://test.com", "GET"),
        ("http://test.com.hack", "POST"),
        ("localhost", "DELETE"),
        ("hello.com.hack", "GET"),
        ("http://test.com", "DELETE"),
        ("http://test.com", "PUT"),
    ],
)
def test_cors_non_allow_origin_header(
    client: TestClient, db_state_item_empty: dict, origin: str, method: str
):
    state_id = db_state_item_empty[0]["id"]
    response = client.options(
        f"/{state_id}",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
        },
    )

    assert response.status_code == 400, (
        f"Unexpected response {response.status_code}: {response.text}"
    )


def test_get_app_state_id_not_found(client: TestClient):
    state_id = "abcdef1234567891"
    response = client.get(f"/{state_id}")

    assert response.status_code == 404, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    assert response.json() == {"error": "Not Found", "message": "State not found"}


def test_get_app_state_bad_id(client: TestClient):
    state_id = "abcdef123456"
    response = client.get(f"/{state_id}")

    assert response.status_code == 400, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    assert data == {
        "detail": [
            {
                "ctx": {
                    "min_length": 16,
                },
                "input": "abcdef123456",
                "loc": [
                    "path",
                    "state_id",
                ],
                "msg": "String should have at least 16 characters",
                "type": "string_too_short",
            }
        ],
        "error": "Validation Error",
        "message": "Invalid request payload",
    }

    state_id = "123456678994563214"
    response = client.get(f"/{state_id}")

    assert response.status_code == 400, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    assert data == {
        "detail": [
            {
                "ctx": {
                    "max_length": 16,
                },
                "input": "123456678994563214",
                "loc": [
                    "path",
                    "state_id",
                ],
                "msg": "String should have at most 16 characters",
                "type": "string_too_long",
            }
        ],
        "error": "Validation Error",
        "message": "Invalid request payload",
    }
