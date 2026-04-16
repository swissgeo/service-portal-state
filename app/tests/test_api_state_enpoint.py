import re
from typing import TYPE_CHECKING

from app.schemas.state import get_app_state_versions

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient


def test_save_app_state(client: TestClient):
    payload = {
        "version": "1.0",
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
    }

    response = client.post("/api/state", json=payload)

    # -------------------------
    # HTTP contract
    # -------------------------
    assert response.status_code == 200, (
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
    response2 = client.post("/api/state", json=payload)
    assert response2.status_code == 200, (
        f"Unexpected response {response2.status_code}: {response2.json()}"
    )
    assert response2.json()["id"] == data["id"]


def test_save_app_state_minor_deprecated_version(app: FastAPI, client: TestClient):
    def override_versions() -> list[str]:
        return ["1.1"]

    app.dependency_overrides[get_app_state_versions] = override_versions
    payload = {
        "version": "1.0",
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
    }

    response = client.post("/api/state", json=payload)

    # -------------------------
    # HTTP contract
    # -------------------------
    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # -------------------------
    # Response shape
    # -------------------------
    assert data == {
        "id": data["id"],
        "deprecated": True,
        "warning": "Version 1.0 is not the latest version of the state object "
        "and may be deprecated in the future. Please use the latest "
        "version 1.1 of the state object to avoid potential issues in "
        "the future.",
    }


def test_save_app_state_major_deprecated_version(client: TestClient):
    payload = {
        "version": "0.9",  # deprecated version
        "state": {},
    }

    response = client.post("/api/state", json=payload)

    assert response.status_code == 400, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    # strict error contract
    assert data == {
        "error": "Bad Request",
        "message": "Version 0.9 is a deprecated version of the state object which "
        "is not supported anymore. Please use the latest version 1.0 of "
        "the state object.",
    }


def test_get_app_state(client: TestClient):
    state_id = "abcdef1234567891"
    response = client.get(f"/api/state/{state_id}")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    assert data == {"id": state_id, "state": {}, "version": "1.0"}


def test_get_app_state_bad_id(client: TestClient):
    state_id = "abcdef123456"
    response = client.get(f"/api/state/{state_id}")

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
    response = client.get(f"/api/state/{state_id}")

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
