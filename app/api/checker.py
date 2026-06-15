from fastapi import APIRouter

from app.schemas.checker import Checker
from app.version import __version__

router = APIRouter()


@router.get("/checker", summary="Kubernetes Probe", tags=["Internal"], include_in_schema=False)
async def get_checker() -> Checker:
    """Simple checker endpoint to be used by kubernetes probes"""
    return Checker(success=True, message="OK", version=__version__)
