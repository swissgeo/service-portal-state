from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

import pytest

from app.main import app_factory

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI


@pytest.fixture
def app():
    return app_factory()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:

    with TestClient(app) as client:
        yield client
