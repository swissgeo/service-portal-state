from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_checker() -> None:
    response = client.get("/checker")
    assert response.status_code == 200
