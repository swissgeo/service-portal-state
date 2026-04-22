from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient


def test_api_checker_endpoint(app: FastAPI, client: TestClient):
    response = client.get(app.url_path_for("get_checker"))
    assert response.status_code == 200
