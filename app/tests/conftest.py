from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

import pytest

from app.main import app_factory
from app.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI


@pytest.fixture
def app():
    return app_factory(
        Settings(
            cors_origins=["http://testserver"],
            cors_method=["*"],
            cors_headers=["*"],
            cors_max_age=600,
            aws_endpoint_url="http://test",
            aws_dynamodb_table_name="test-table",
        )
    )


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:

    with TestClient(app) as client:
        yield client
