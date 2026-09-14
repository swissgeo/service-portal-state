import logging
import os
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Annotated, Any

from opentelemetry import trace

from fastapi import APIRouter, Depends, FastAPI, Response, status

from app.syntheticz.exceptions import SyntheticError
from app.syntheticz.schemas import (
    Syntheticz,
    SyntheticzExternalSystem,
    SyntheticzService,
    SyntheticzStatus,
)

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

# Attribute added to every OTEL signal emitted during a synthetic check, so that synthetic
# traffic can be filtered out of the regular service telemetry.
# See https://swissgeoplatform.atlassian.net/wiki/spaces/GEOIN/pages/826769409
SYNTHETIC_ATTRIBUTE = "synthetic"

DEFAULT_PATH = "/syntheticz"

# Environment variable used when no explicit name is passed to the plugin.
SERVICE_NAME_ENV_VAR = "SERVICE_NAME"

# A synthetic check function. It may be sync or async and may declare FastAPI dependencies.
# It returns the healthy external systems (a list of names, or a mapping already built by the
# caller), or None when the service has no external system to report. It raises SyntheticError
# when one or more external systems are unhealthy.
SyntheticCheck = Callable[..., Awaitable[Any] | Any]


def _service_name(name: str | None) -> str:
    """Return the explicit name, or fall back to the SERVICE_NAME environment variable."""
    return name or os.environ.get(SERVICE_NAME_ENV_VAR, "unknown-service")


async def mark_synthetic_span() -> None:
    """Mark the request span as synthetic, before the check function runs."""
    trace.get_current_span().set_attribute(SYNTHETIC_ATTRIBUTE, True)  # noqa: FBT003


def _as_up_systems(healthy: Any) -> dict[str, SyntheticzExternalSystem]:
    """Normalize whatever the check function returned into UP external system entries."""
    if healthy is None:
        return {}

    if isinstance(healthy, dict):
        # Already a mapping: either of SyntheticzExternalSystem, or of raw statuses.
        return {
            name: value
            if isinstance(value, SyntheticzExternalSystem)
            else SyntheticzExternalSystem(status=SyntheticzStatus(value))
            for name, value in healthy.items()
        }

    return {name: SyntheticzExternalSystem(status=SyntheticzStatus.UP) for name in healthy}


def build_syntheticz_router(
    check: SyntheticCheck,
    version: str,
    *,
    name: str | None = None,
    path: str = DEFAULT_PATH,
    tags: list[str | Enum] | None = None,
) -> APIRouter:
    """Build the router exposing the synthetic check endpoint.

    Args:
        check: the service specific check function. It must be idempotent and free of side
            effects. It raises SyntheticError with the failed external systems when unhealthy,
            and returns the healthy external system names (or None) otherwise. It may be sync or
            async, and may declare FastAPI dependencies in its signature.
        version: version of the service, reported as `service.version`.
        name: name of the service, reported as `service.name`. Defaults to the SERVICE_NAME
            environment variable.
        path: route path of the endpoint. Note that when the application sets a `root_path`, it
            is prepended by FastAPI, so this must stay relative to it.
        tags: OpenAPI tags for the route.

    Returns:
        APIRouter: a router with a single GET route serving the synthetic check.
    """
    service = SyntheticzService(name=_service_name(name), version=version)

    # The span must be marked before the check dependency runs, hence a router level
    # dependency rather than a statement in the route handler body.
    router = APIRouter(tags=tags or [], dependencies=[Depends(mark_synthetic_span)])

    @router.get(
        path,
        summary="Synthetic Check",
        responses={500: {"model": Syntheticz}},
    )
    async def get_syntheticz(
        response: Response,
        check_result: Annotated[Any, Depends(check)],
    ) -> Syntheticz:
        """Synthetic check endpoint used by the platform monitoring agent.

        Returns 200 when the service and all its external systems are healthy, 500 otherwise.
        The per-system status is reported in the body in both cases.

        This endpoint must not be used for kubernetes probes, use `/checker` instead.
        """
        # Tell CloudFront and any other cache to never serve a cached check result.
        response.headers["Cache-Control"] = "no-store"

        return Syntheticz(
            service=service,
            status=SyntheticzStatus.UP,
            external_systems=_as_up_systems(check_result),
        )

    return router


# NOTE: all configuration arguments are keyword-only, the count is deliberate.
def setup_syntheticz(  # noqa: PLR0913
    app: FastAPI,
    check: SyntheticCheck,
    version: str,
    *,
    name: str | None = None,
    path: str = DEFAULT_PATH,
    tags: list[str | Enum] | None = None,
) -> None:
    """Register the synthetic check endpoint and its exception handler on the application.

    See build_syntheticz_router() for the arguments.
    """
    service = SyntheticzService(name=_service_name(name), version=version)

    async def syntheticz_exception_handler(_request: Any, exc: Exception) -> Response:
        """Turn a SyntheticError into a 500 response carrying the per-system status."""
        assert isinstance(exc, SyntheticError)  # noqa: S101

        logger.error(
            "Synthetic check failed: %s",
            exc.message,
            extra={SYNTHETIC_ATTRIBUTE: True},
        )

        body = Syntheticz(
            service=service,
            status=SyntheticzStatus.DOWN,
            external_systems=exc.as_external_systems(),
        )
        return Response(
            content=body.model_dump_json(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    app.add_exception_handler(SyntheticError, syntheticz_exception_handler)
    app.include_router(
        build_syntheticz_router(check=check, version=version, name=name, path=path, tags=tags)
    )
