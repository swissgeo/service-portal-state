import json
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from app.core.hashing import canonical_hash_bytes_96
from app.tests.conftest import MockGetItemFactory, MockPutItemFactory


@pytest.mark.parametrize(
    "payload",
    [
        {
            "state": {},
        },
        {
            "state": {
                "map": {
                    "center": [2660000, 1190000],
                    "zoom": 1,
                    "rotation": 0,
                }
            },
        },
        {
            "state": {
                "map": {
                    "center": [2660000, 1190000],
                    "zoom": 1,
                    "rotation": 0,
                }
            },
            "layers": [],
        },
        {
            "state": {
                "map": {
                    "zoom": 4,
                }
            },
            "layers": [
                {
                    "layerUrl": "https://services.swissgeo.ch/api/oar/v0/collections/swissgeo.catalog/items/ch.bafu.neophyten-grossbluetiges_heusenkraut?language=de",
                    "type": "dataset",
                }
            ],
        },
        {
            "state": {
                "map": {
                    "center": [2660000, 1190000],
                    "zoom": 1,
                    "rotation": 0,
                },
                "layers": [
                    {
                        "layerUrl": "https://services.swissgeo.ch/api/oar/v0/collections/swissgeo.catalog/items/ch.bafu.neophyten-grossbluetiges_heusenkraut?language=de",
                        "type": "dataset",
                        "isVisible": True,
                        "opacity": 0.75,
                        "dimensions": {"time": {"currentValue": "current"}},
                    }
                ],
            },
        },
    ],
)
def test_save_app_state(client: TestClient, payload: dict):

    response = client.post("", json=payload)

    # -------------------------
    # HTTP contract
    # -------------------------
    assert response.status_code == 201, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # -------------------------
    # Response shape
    # -------------------------
    assert data == {"id": data["id"]}

    # -------------------------
    # Hash format (96-bit base64url)
    # -------------------------
    assert re.fullmatch(r"[A-Za-z0-9_-]{16}", data["id"]), f"Unexpected hash format: {data['id']}"

    # -------------------------
    # Determinism check
    # -------------------------

    response2 = client.post("", json=payload)
    assert response2.status_code == 200, (
        f"Unexpected response {response2.status_code}: {response2.json()}"
    )
    assert response2.json()["id"] == data["id"]


def test_save_app_state_already_exists(client: TestClient, db_state_item_full: tuple[dict, str]):
    state_id = db_state_item_full[0]["id"]

    payload = json.loads(db_state_item_full[1])

    response = client.post("", json=payload)

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"] == "application/json"
    assert response.json()["id"] == state_id


@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing state
        {"state": "not an object"},  # state is not an object
        {"state": {"map": "not an object"}},  # map is not an object
        {"state": {"layers": "not a list"}},  # layers is not a list
        {"state": {"layers": [{"type": "dataset"}]}},  # missing required layer fields
        {"hello world": "unexpected field"},  # unexpected top-level field
        "Not a JSON object",  # not a JSON object
        ["list instead of object"],  # not a JSON object
    ],
)
def test_save_app_state_invalid_payload(client: TestClient, payload: dict):
    response = client.post("", json=payload)

    assert response.status_code == 400, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"] == "application/json"
    assert response.json()["error"] == "Validation Error"
    assert response.json()["message"] == "Invalid request payload"


def test_save_app_state_collision(
    app: FastAPI,
    mock_dynamodb_client_put_item: MockPutItemFactory,
    mock_dynamodb_client_get_item: MockGetItemFactory,
):
    client = TestClient(app, raise_server_exceptions=False)
    state = {"state": {}}
    _, state_id = canonical_hash_bytes_96(json.dumps(state).encode("utf-8"))
    mock_client = mock_dynamodb_client_put_item(
        client_error={"Code": "ConditionalCheckFailedException", "Message": "Item already exists"},
    )
    mock_dynamodb_client_get_item(
        {
            "Item": {
                "id": {"S": state_id},
                "full_hash": {"S": "dummy-hash-12345" * 4},
                "major_version": {"N": "1"},
                "created": {"S": "2024-01-01T00:00:00Z"},
                "last_accessed": {"S": "2024-01-01T00:00:00Z"},
                "state": {"M": {}},
            }
        },
        mock_client=mock_client,
    )
    response = client.post("", json=state)

    assert response.status_code == 500, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"] == "application/json"
    assert response.json()["error"] == "internal service error"
    assert response.json()["message"] == "An unexpected error occurred"
