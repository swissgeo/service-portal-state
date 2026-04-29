from opentelemetry import metrics

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

router = APIRouter()


OPENAPI__TAG = "Application State"

# TODO re-asses the usage of such metric
meter = metrics.get_meter(__name__)
save_200_meter = meter.create_counter(
    "portal.state.save.duplicate", unit="1", description="Counts of save state that already exists"
)
save_201_meter = meter.create_counter(
    "portal.state.save.new", unit="1", description="Counts of new save state"
)
get_meter = meter.create_counter(
    "portal.state.get", unit="1", description="Counts of get sate event"
)


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
        save_201_meter.add(
            1, attributes={"headers.user-agent": request.headers.get("User-Agent", "unknown")}
        )
    else:
        save_200_meter.add(
            1,
            attributes={
                "state.id": state_id,
                "headers.user-agent": request.headers.get("User-Agent", "unknown"),
            },
        )

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
    tags=[OPENAPI__TAG],
)
async def get_app_state(
    request: Request, state_id: StateId, app: StateServiceDep, bg_tasks: BackgroundTasks
) -> GetAppStateResponse:
    """Retrieve an application state by ID"""

    db_item = await app.get_app_state(state_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="State not found")
    get_meter.add(
        1,
        attributes={
            "state.id": state_id,
            "headers.user-agent": request.headers.get("User-Agent", "unknown"),
        },
    )
    bg_tasks.add_task(app.update_last_accessed, db_item)

    return GetAppStateResponse.from_db_state_item(db_item)
