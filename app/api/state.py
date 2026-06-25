from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status

from app.core.state_service import StateServiceDep
from app.schemas.errors import ErrorResponse
from app.schemas.state import (
    GetAppStateResponse,
    SaveAppStateRequest,
    SaveAppStateResponse,
    StateId,
    StateItem,
)

STATE_TAG = "Application State"

router = APIRouter(tags=[STATE_TAG])


@router.post(
    "/",
    summary="Save Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    responses={400: {"model": ErrorResponse}},
)
async def post_app_state(
    request: Request,
    payload: SaveAppStateRequest,
    app: StateServiceDep,
    response: Response,
) -> SaveAppStateResponse:
    """Save the given application state"""

    full_hash, state_id = request.state.payload_hash

    if await app.save_app_state(
        state_id=state_id,
        full_hash=full_hash,
        state=StateItem(**payload.model_dump(by_alias=True)),
    ):
        response.status_code = status.HTTP_201_CREATED

    return SaveAppStateResponse(id=state_id)


@router.get(
    "/{state_id}",
    summary="Get Application State",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    response_model_by_alias=True,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_app_state(
    response: Response,
    state_id: StateId,
    app: StateServiceDep,
    bg_tasks: BackgroundTasks,
) -> GetAppStateResponse:
    """Retrieve an application state by ID"""

    db_item = await app.get_app_state(state_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="State not found")

    bg_tasks.add_task(app.update_last_accessed, db_item)

    # Set the cache control header, note that an answer can never change because
    # we use a hash of the state content, so we can cache it forever.
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    return GetAppStateResponse.from_db_state_item(db_item)
