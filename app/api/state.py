from fastapi import APIRouter, Request

from app.schemas.errors import ErrorResponse
from app.schemas.state import (
    GetAppStateResponse,
    SaveAppStateRequest,
    SaveAppStateResponse,
    StateId,
    StateV1,
)

router = APIRouter()

OPENAPI__TAG = "Application State"


@router.post(
    "/",
    summary="Save Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    responses={400: {"model": ErrorResponse}},
    tags=[OPENAPI__TAG],
)
async def post_app_state(
    request: Request,
    payload: SaveAppStateRequest,  # noqa: ARG001 temporary until we use the payload
) -> SaveAppStateResponse:
    """Save the given application state"""

    state_id = request.state.payload_hash[1]
    return SaveAppStateResponse(id=state_id)


@router.get(
    "/{state_id}",
    summary="Get Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=[OPENAPI__TAG],
)
async def get_app_state(state_id: StateId) -> GetAppStateResponse:  # noqa: ARG001 temporary until we use the state_id
    """Retrieve an application state by ID"""
    return GetAppStateResponse(state=StateV1())
