from fastapi.testclient import TestClient

from app.api.internal import INTERNAL_TAG
from app.api.state import STATE_TAG


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


def test_default_spec_excludes_internal_routes(client: TestClient):
    spec = client.get("openapi.json").json()

    assert "/checker" not in spec["paths"]


def test_default_spec_excludes_internal_tag(client: TestClient):
    spec = client.get("openapi.json").json()

    tag_names = [t["name"] for t in spec["tags"]]
    assert INTERNAL_TAG not in tag_names
    assert STATE_TAG in tag_names


def test_internal_openapi_json(client: TestClient):
    response = client.get("internal/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_internal_spec_contains_checker_route(client: TestClient):
    spec = client.get("internal/openapi.json").json()

    assert "/checker" in spec["paths"]


def test_internal_spec_excludes_state_routes(client: TestClient):
    spec = client.get("internal/openapi.json").json()

    paths = spec["paths"]
    assert "/" not in paths
    assert "/{state_id}" not in paths


def test_internal_spec_excludes_state_tag(client: TestClient):
    spec = client.get("internal/openapi.json").json()

    tag_names = [t["name"] for t in spec["tags"]]
    assert STATE_TAG not in tag_names
    assert INTERNAL_TAG in tag_names


def test_internal_docs(client: TestClient):
    response = client.get("internal/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_internal_redoc(client: TestClient):
    response = client.get("internal/redoc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


# NOTE: we cannot test whether the internal spec is not served when disabled,
# as the application is initialized before the settings are mocked. So this
# that to do this test we would need to change the application and do the
# disabling of spec serving at request time and not at application startup.
# This would require a refactoring of the application and increase its complexity.
# just for testing purposes.
