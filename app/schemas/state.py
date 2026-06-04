import math
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyUrl, BaseModel, Field

CoordinateX = Annotated[float, Field(ge=0, description="Coordinate x in LV95 / EPSG:2056 (meters)")]
CoordinateY = Annotated[float, Field(ge=0, description="Coordinate y in LV95 / EPSG:2056 (meters)")]


class MapState(BaseModel):
    center: tuple[CoordinateX, CoordinateY] | None = Field(
        default=None,
        description="Center of the map in [x, y] coordinates in lv95 / EPSG:2056",
        examples=[(2660000, 1190000)],
    )
    zoom: float | None = Field(
        default=None, description="Zoom level of the map", examples=[1], ge=1, le=13
    )
    rotation: float | None = Field(
        default=None,
        description="Rotation of the map in radian",
        examples=[0],
        ge=0,
        le=2 * math.pi,
    )


class TimeDimension(BaseModel):
    current_value: datetime | Literal["current"] | None = Field(
        alias="currentValue",
        default=None,
        description="Current selected time value",
        examples=["current"],
    )


class LayerDimensionsState(BaseModel):
    time: TimeDimension = Field(
        default_factory=TimeDimension, description="Time dimension with current value"
    )


class LayerTypeEnum(StrEnum):
    DATASET = "dataset"
    GPS = "gpx"
    KML = "kml"


class LayerState(BaseModel):
    # TODO should we restrict to only http and https ?
    layer_url: AnyUrl = Field(
        alias="layerUrl",
        description="URL of the layer to be displayed on the map",
        examples=[
            "https://services.swissgeo.ch/api/oar/v0/collections/swissgeo.catalog/items/ch.bafu.neophyten-grossbluetiges_heusenkraut?language=de"
        ],
    )
    type: LayerTypeEnum = Field(
        description="Type of the layer (e.g. dataset, gpx, kml)",
        examples=["dataset"],
    )
    is_visible: bool | None = Field(
        alias="isVisible",
        default=None,
        description="Whether the layer is visible on the map",
    )
    opacity: float | None = Field(
        default=None,
        description="Opacity of the layer (between 0 and 1)",
        examples=[0.75],
        ge=0,
        le=1,
    )
    dimensions: LayerDimensionsState = Field(
        default_factory=LayerDimensionsState,
        description="Dimensions of the layer (e.g. time dimension with current value)",
    )


class StateV1(BaseModel):
    """State object of the application"""

    map: MapState = Field(default_factory=MapState, description="State of the map")
    layers: list[LayerState] = Field(
        default_factory=list, description="List of layers to be displayed on the map"
    )


State = StateV1

StateId = Annotated[
    str,
    Field(
        description="ID of the state",
        examples=["abcef12345678910"],
        min_length=16,
        max_length=16,
    ),
]


class StateItem(BaseModel):
    state: State


class SaveAppStateRequest(BaseModel):
    state: State = Field(description="State of the application to save")


WarningType = Annotated[
    str,
    Field(
        description="Warning message about deprecation flag",
        default="",
    ),
]


class SaveAppStateResponse(BaseModel):
    id: StateId = Field(
        description="ID of the saved state, to be used to retrieve the state later",
    )
    deprecated: bool = Field(
        description="When true the application state version provided is deprecated",
        default=False,
        examples=[],
    )
    warning: WarningType = ""


class GetAppStateResponse(StateItem):
    deprecated: bool = Field(
        description="When true the application state version is deprecated",
        default=False,
    )
    warning: WarningType = ""

    @classmethod
    def from_db_state_item(cls, state: StateItem) -> GetAppStateResponse:
        return cls.model_validate(state.model_dump(by_alias=True))
