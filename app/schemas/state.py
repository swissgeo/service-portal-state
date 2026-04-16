import math
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from anyio.functools import lru_cache
from pydantic import AnyUrl, BaseModel, Field, PositiveFloat, field_validator

SEMVER_REGEX = re.compile(r"^\d+\.\d+$")


@lru_cache
def get_app_state_versions() -> list[str]:
    """Application State object supported versions.

    List all supported version for the state object.
    """
    return ["1.0"]


CoordinateX = Annotated[
    PositiveFloat, Field(description="Coordinate x in LV95 / EPSG:2056 (meters)")
]
CoordinateY = Annotated[
    PositiveFloat, Field(description="Coordinate y in LV95 / EPSG:2056 (meters)")
]


class MapState(BaseModel):
    center: tuple[CoordinateX, CoordinateY] = Field(
        default=(2660000, 1190000),
        description="Center of the map in [x, y] coordinates in lv95 / EPSG:2056",
        examples=[(2660000, 1190000)],
    )
    zoom: float = Field(default=1, description="Zoom level of the map", examples=[1], ge=1, le=13)
    rotation: float = Field(
        default=0, description="Rotation of the map in radian", examples=[0], ge=0, le=2 * math.pi
    )


class TimeDimension(BaseModel):
    current_value: datetime | Literal["current"] = Field(
        alias="currentValue",
        default="current",
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
    is_visible: bool = Field(
        alias="isVisible",
        default=True,
        description="Whether the layer is visible on the map",
    )
    opacity: float = Field(
        default=1, description="Opacity of the layer (between 0 and 1)", examples=[0.75], ge=0, le=1
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


StateVersion = Annotated[
    str,
    Field(
        description="Version of the state object: `major.minor`",
        examples=["1.0"],
    ),
]


class SaveAppStateRequest(BaseModel):
    version: StateVersion
    state: StateV1 = Field(description="State of the application to save")

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if SEMVER_REGEX.fullmatch(v) is None:
            raise ValueError("Version must be in the format X.Y (e.g. 1.2)")
        return v


StateId = Annotated[
    str,
    Field(
        description="ID of the state",
        examples=["abcef12345678910"],
        min_length=16,
        max_length=16,
    ),
]


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


class GetAppStateResponse(BaseModel):
    id: StateId
    version: StateVersion
    state: StateV1
    deprecated: bool = Field(
        description="When true the application state version is deprecated",
        default=False,
    )
    warning: WarningType = ""
