from fastapi import APIRouter, Response, status

from app.core.syntheticz_service import SyntheticzServiceDep
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
    status_code=200,
    responses={500: {"model": Syntheticz}},
)
async def get_syntheticz(
    response: Response,
    syntheticz: SyntheticzServiceDep,
) -> Syntheticz:
    response.headers["Cache-Control"] = "no-store"

    health = await syntheticz.check()

    if health.status != SyntheticzStatus.UP:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return health
