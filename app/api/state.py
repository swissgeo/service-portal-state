from fastapi import APIRouter, HTTPException, Request

from app.schemas.errors import ErrorResponse
from app.schemas.state import (
    GetAppStateResponse,
    SaveAppStateRequest,
    SaveAppStateResponse,
    StateId,
    StateV1,
    Version,
)

router = APIRouter()

OPENAPI__TAG = "Application State"


def check_version(version: int) -> None:
    if version != 1:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unsupported Version",
                "message": f"Version {version} is not supported. Supported versions: [1]",
            },
        )


@router.post(
    "/api/v{version}/state",
    summary="Save Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    responses={400: {"model": ErrorResponse}},
    tags=[OPENAPI__TAG],
)
async def post_app_state(
    request: Request,
    version: Version,
    payload: SaveAppStateRequest,  # noqa: ARG001 temporary until we use the payload
) -> SaveAppStateResponse:
    """Save the given application state"""

    check_version(version)

    state_id = request.state.payload_hash[1]
    return SaveAppStateResponse(id=state_id)


@router.get(
    "/api/v{version}/state/{state_id}",
    summary="Get Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=[OPENAPI__TAG],
)
async def get_app_state(version: Version, state_id: StateId) -> GetAppStateResponse:  # noqa: ARG001 temporary until we use the state_id
    """Retrieve an application state by ID"""
    check_version(version)
    return GetAppStateResponse(state=StateV1())
