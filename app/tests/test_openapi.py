from fastapi.testclient import TestClient


def test_get_openapi_json(client: TestClient):
    response = client.get("openapi.json")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("application/json")


def test_get_openapi_doc(client: TestClient):
    response = client.get("docs")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("text/html")


def test_get_openapi_redoc(client: TestClient):
    response = client.get("redoc")

    assert response.status_code == 200, (
        f"Unexpected response {response.status_code}: {response.json()}"
    )
    assert response.headers["content-type"].startswith("text/html")
