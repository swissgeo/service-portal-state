import json
import logging
import logging.config
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aioboto3
import yaml

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute

from app.api import internal, state
from app.api.internal import INTERNAL_TAG
from app.api.state import STATE_TAG
from app.core.exceptions import register_exception_handlers
from app.middlewares.canonical_hash import CanonicalHashMiddleware
from app.otel import initialize_instrumentation, shutdown_otel
from app.settings import get_settings
from app.version import __version__

logger = logging.getLogger(__name__)

settings = get_settings()


def get_logging_cfg(config_file: Path) -> dict:  # pragma: no cover
    """Load and parse logging configuration from the given file"""
    config = yaml.safe_load(config_file.read_text())

    logger.info("Loaded logging configuration from file %s", config_file)
    return config


def _remove_422(schema: dict[str, Any]) -> None:
    for method_item in schema.get("paths", {}).values():
        for param in method_item.values():
            param.get("responses", {}).pop("422", None)


def _build_default_schema(app: FastAPI) -> dict[str, Any]:
    routes = [r for r in app.routes if not (isinstance(r, APIRoute) and INTERNAL_TAG in r.tags)]
    tags = [t for t in (app.openapi_tags or []) if t.get("name") != INTERNAL_TAG]
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        routes=routes,
        tags=tags,
        servers=app.servers,
    )
    _remove_422(schema)
    return schema


def _build_internal_schema(app: FastAPI) -> dict[str, Any]:
    routes = [r for r in app.routes if isinstance(r, APIRoute) and INTERNAL_TAG in r.tags]
    tags = [t for t in (app.openapi_tags or []) if t.get("name") == INTERNAL_TAG]
    schema = get_openapi(
        title=f"{app.title} - Internal",
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        routes=routes,
        tags=tags,
        servers=app.servers,
    )
    _remove_422(schema)
    return schema


def setup_openapi(app: FastAPI) -> None:
    """Configure split OpenAPI specs and register internal doc endpoints.

    The default spec (/docs, /openapi.json) excludes Internal-tagged routes.
    The internal spec (/internal/openapi.json, /internal/docs, /internal/redoc)
    contains only Internal-tagged routes.

    Also removes 422 responses replaced by 400 via our exception handler.
    See https://github.com/fastapi/fastapi/discussions/6695
    """
    _internal_schema: dict[str, Any] | None = None

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema  # pragma: no cover
        app.openapi_schema = _build_default_schema(app)
        return app.openapi_schema

    def internal_openapi() -> dict[str, Any]:
        nonlocal _internal_schema
        if _internal_schema is None:
            _internal_schema = _build_internal_schema(app)
        return _internal_schema

    app.openapi = custom_openapi  # ty:ignore[invalid-assignment]

    @app.get("/internal/openapi.json", include_in_schema=False)
    async def internal_openapi_schema() -> Response:
        return Response(content=json.dumps(internal_openapi()), media_type="application/json")

    @app.get("/internal/docs", include_in_schema=False)
    async def internal_docs() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/internal/openapi.json", title=f"{app.title} - Internal Docs"
        )

    @app.get("/internal/redoc", include_in_schema=False)
    async def internal_redoc() -> HTMLResponse:
        return get_redoc_html(
            openapi_url="/internal/openapi.json", title=f"{app.title} - Internal Docs"
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup code (runs before application startup)

    settings = get_settings()

    logger.info("Initializing DynamoDB session")
    app.state.dynamodb_session = aioboto3.Session(region_name=settings.aws_region)

    logger.info("Startup tasks completed")

    yield

    # Shutdown code (runs after application shutdown)
    shutdown_otel()

    logger.info("Shutdown tasks completed")


# First configure logging for local server if needed
if settings.logging_enable_dev_server_logging:  # pragma: no cover
    if settings.logging_config_file:
        log_config = get_logging_cfg(settings.logging_config_file)
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(level=logging.INFO)

if settings.logging_handlers_level is not None:  # pragma: no cover
    for handler in logging.getLogger().handlers:
        handler.setLevel(settings.logging_handlers_level)


app = FastAPI(
    title="Service State Portal",
    summary="Save and retrieve application state for web-portal",
    description="""This service allow the web-portal application to save its state and retrieve
    it later on.
    """,
    version=__version__,
    contact={"name": "swissgeo", "url": "https://www.swissgeo.ch/infos"},
    license_info={
        "name": "BSD 3-Clause License",
        "identifier": "BSD-3-Clause",
    },
    openapi_tags=[
        {"name": INTERNAL_TAG, "description": "Internal APIs not for external uses"},
        {"name": STATE_TAG, "description": "Application State Operations"},
    ],
    lifespan=lifespan,
    root_path=settings.root_path,
)
setup_openapi(app)

# Register exceptions handlers
register_exception_handlers(app)

# Add middlewares
app.add_middleware(CanonicalHashMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=settings.cors_method,
    allow_headers=settings.cors_headers,
    max_age=settings.cors_max_age,
)

# Register routes
app.include_router(internal.router)
app.include_router(state.router)

# Setup OTEL instrumentation
initialize_instrumentation(app)
