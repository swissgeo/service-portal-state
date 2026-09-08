from opentelemetry import trace

from fastapi import APIRouter, Response, status

from app.core.syntheticz_service import SYNTHETIC_ATTRIBUTE, SyntheticzCheckerDep
from app.schemas.checker import Checker
from app.schemas.syntheticz import Syntheticz, SyntheticzStatus
from app.version import __version__

INTERNAL_TAG = "Internal"

router = APIRouter(tags=[INTERNAL_TAG])


@router.get("/checker", summary="Kubernetes Probe")
async def get_checker() -> Checker:
    """Simple checker endpoint to be used by kubernetes probes"""
    return Checker(success=True, message="OK", version=__version__)


@router.get(
    "/syntheticz",
    summary="Synthetic Check",
    responses={500: {"model": Syntheticz}},
)
async def get_syntheticz(response: Response, checker: SyntheticzCheckerDep) -> Syntheticz:
    """Synthetic check endpoint used by the platform monitoring agent.

    Returns 200 when the service and all its external systems are healthy, 500 otherwise.
    The per-system status is reported in the body in both cases.

    This endpoint must not be used for kubernetes probes, use `/checker` instead.
    """
    trace.get_current_span().set_attribute(SYNTHETIC_ATTRIBUTE, True)  # noqa: FBT003

    result = await checker.check()

    if result.status is not SyntheticzStatus.UP:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Tell CloudFront and any other cache to never serve a cached check result.
    response.headers["Cache-Control"] = "no-store"

    return result
