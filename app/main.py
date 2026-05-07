import logging
import logging.config
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
import yaml

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api import checker, state
from app.core.exceptions import register_exception_handlers
from app.middlewares.canonical_hash import CanonicalHashMiddleware
from app.otel import initialize_instrumentation, shutdown_otel
from app.settings import get_settings
from app.version import __version__

logger = logging.getLogger(__name__)

settings = get_settings()


def get_logging_cfg(config_file: str) -> dict:  # pragma: no cover
    """Load and parse logging configuration from the given file"""
    with open(config_file, encoding="utf-8") as fd:
        config = yaml.safe_load(fd.read())

    logger.info("Loaded logging configuration from file %s", config_file)
    return config


def customize_openapi(app: FastAPI) -> None:
    """Customize openapi

    Hack to get rid of the 422 in the openapi which is replaced by 400 by our exception handler
    See https://github.com/fastapi/fastapi/discussions/6695
    """

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema  # pragma: no cover

        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        for method_item in app.openapi_schema.get("paths", {}).values():
            for param in method_item.values():
                responses = param.get("responses", {})
                # remove 422 response, also can remove other status code
                responses.pop("422", None)
        return app.openapi_schema

    app.openapi = custom_openapi  # ty:ignore[invalid-assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup code (runs before application startup)

    settings = get_settings()

    logger.info("Initializing DynamoDB session")
    app.state.dynamodb_session = aioboto3.Session(region_name=settings.aws_region)

    logger.info("Startup tasks completed")

    yield

    # Shutdown code (runs after application shutdown)
    shutdown_otel(settings)

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
        {"name": "Internal", "description": "Internal APIs not for external uses"},
        {"name": "Application State", "description": "Application State Operations"},
    ],
    lifespan=lifespan,
    root_path=settings.root_path,
)
customize_openapi(app)

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
app.include_router(checker.router)
app.include_router(state.router)


# Setup OTEL instrumentation
initialize_instrumentation(settings, app)
