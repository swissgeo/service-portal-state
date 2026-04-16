from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_checker(client: TestClient):
    response = client.get("/checker")
    assert response.status_code == 200
