from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.utils import has_same_major
from app.schemas.errors import ErrorResponse
from app.schemas.state import (
    GetAppStateResponse,
    SaveAppStateRequest,
    SaveAppStateResponse,
    StateId,
    StateV1,
    get_app_state_versions,
)

router = APIRouter()


@router.post(
    "/api/state",
    summary="Save Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    responses={400: {"model": ErrorResponse}},
    tags=["Application State"],
)
async def post_app_state(
    request: Request,
    payload: SaveAppStateRequest,
    versions: Annotated[list[str], Depends(get_app_state_versions)],
) -> SaveAppStateResponse:
    """Save the given application state"""

    if not has_same_major(payload.version, versions):
        deprecated = (
            f"Version {payload.version} is a deprecated version of the state object which is "
            f"not supported anymore. Please use the latest version {versions[0]} "
            "of the state object."
        )
        raise HTTPException(status_code=400, detail=deprecated)

    state_id = request.state.payload_hash[1]
    if payload.version not in versions:
        warning = (
            f"Version {payload.version} is not the latest version of the state object and may "
            "be deprecated in the future. Please use the latest version "
            f"{versions[0]} of the state object to avoid potential issues in the "
            "future."
        )
        return SaveAppStateResponse(id=state_id, deprecated=True, warning=warning)

    return SaveAppStateResponse(id=state_id)


@router.get(
    "/api/state/{state_id}",
    summary="Get Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Application State"],
)
async def get_app_state(state_id: StateId) -> GetAppStateResponse:
    """Retrieve an application state by ID"""
    return GetAppStateResponse(id=state_id, version="1.0", state=StateV1())
