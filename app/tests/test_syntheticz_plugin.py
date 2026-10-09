"""Tests of the generic synthetic check plugin, independent of this service's own check."""

from collections.abc import Callable

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import pytest

from app.syntheticz import SyntheticError, setup_syntheticz

VERSION = "v1.2.0"


def build_client(check: Callable, name: str | None = "my-service") -> TestClient:
    app = FastAPI()
    setup_syntheticz(app, check=check, version=VERSION, name=name)
    return TestClient(app)


def test_healthy_check_returns_200():
    async def check() -> list[str]:
        return ["s3", "sqs"]

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 200
    assert response.json() == {
        "service": {"name": "my-service", "version": VERSION},
        "status": "UP",
        "external_systems": {"s3": {"status": "UP"}, "sqs": {"status": "UP"}},
    }


def test_synthetic_error_returns_500_with_failed_systems():
    async def check() -> None:
        raise SyntheticError(failed=["efs"])

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 500
    assert response.json() == {
        "service": {"name": "my-service", "version": VERSION},
        "status": "DOWN",
        "external_systems": {"efs": {"status": "DOWN"}},
    }


def test_synthetic_error_accepts_reason_mapping():
    async def check() -> None:
        raise SyntheticError(failed={"efs": "mount timed out", "s3": "403"})

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 500
    assert response.json()["external_systems"] == {
        "efs": {"status": "DOWN"},
        "s3": {"status": "DOWN"},
    }


def test_sync_check_function_is_supported():
    def check() -> list[str]:
        return ["s3"]

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 200
    assert response.json()["external_systems"] == {"s3": {"status": "UP"}}


def test_check_without_external_systems_returns_empty_mapping():
    async def check() -> None:
        return None

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 200
    assert response.json()["external_systems"] == {}


def test_check_function_can_declare_fastapi_dependencies():
    """The check is wired as a real dependency, so it can itself depend on other providers."""

    async def get_flag() -> str:
        return "injected"

    async def check(flag: str = Depends(get_flag)) -> list[str]:
        return [flag]

    response = build_client(check).get("/syntheticz")

    assert response.json()["external_systems"] == {"injected": {"status": "UP"}}


def test_service_name_falls_back_to_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_NAME", "env-service")

    async def check() -> None:
        return None

    response = build_client(check, name=None).get("/syntheticz")

    assert response.json()["service"] == {"name": "env-service", "version": VERSION}


def test_explicit_name_wins_over_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_NAME", "env-service")

    async def check() -> None:
        return None

    response = build_client(check, name="explicit-service").get("/syntheticz")

    assert response.json()["service"]["name"] == "explicit-service"


def test_service_name_defaults_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SERVICE_NAME", raising=False)

    async def check() -> None:
        return None

    response = build_client(check, name=None).get("/syntheticz")

    assert response.json()["service"]["name"] == "unknown-service"


def test_response_is_never_cached():
    async def healthy() -> None:
        return None

    async def failing() -> None:
        raise SyntheticError(failed=["s3"])

    assert build_client(healthy).get("/syntheticz").headers["Cache-Control"] == "no-store"
    assert build_client(failing).get("/syntheticz").headers["Cache-Control"] == "no-store"


def test_synthetic_error_requires_a_failed_system():
    """A SyntheticError carrying no dependency would tell the monitoring system nothing."""
    with pytest.raises(ValueError, match="at least one failed external system"):
        SyntheticError(failed=[])


def test_check_can_return_an_explicit_status_mapping():
    """A check may build the external systems mapping itself, e.g. to report a degraded system."""

    async def check() -> dict[str, str]:
        return {"s3": "UP", "sqs": "UP"}

    response = build_client(check).get("/syntheticz")

    assert response.status_code == 200
    assert response.json()["external_systems"] == {"s3": {"status": "UP"}, "sqs": {"status": "UP"}}


def test_endpoint_path_can_be_customised():
    async def check() -> None:
        return None

    app = FastAPI()
    setup_syntheticz(
        app, check=check, version=VERSION, name="my-service", path="/healthz/syntheticz"
    )
    client = TestClient(app)

    assert client.get("/healthz/syntheticz").status_code == 200
    assert client.get("/syntheticz").status_code == 404


def test_path_is_relative_to_the_application_root_path():
    """FastAPI prepends `root_path`, so the configured path must stay relative to it."""

    async def check() -> None:
        return None

    app = FastAPI(root_path="/api/wps/v1/state")
    setup_syntheticz(app, check=check, version=VERSION, name="my-service")
    client = TestClient(app)

    assert client.get("/api/wps/v1/state/syntheticz").status_code == 200
