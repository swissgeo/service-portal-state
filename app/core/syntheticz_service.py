import logging
from typing import Annotated

from opentelemetry import trace
from types_aiobotocore_dynamodb import DynamoDBClient

from fastapi import Depends

from app.core.db import DynamoDBClientDep
from app.schemas.syntheticz import (
    Syntheticz,
    SyntheticzExternalSystem,
    SyntheticzServiceDetails,
    SyntheticzStatus,
)
from app.settings import SettingsDep
from app.version import __version__

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)


class SyntheticzService:
    def __init__(self, client: DynamoDBClient, settings: SettingsDep) -> None:
        self._client = client
        self._table_name = settings.aws_dynamodb_table_name

    async def check(self) -> Syntheticz:
        dynamodb = "dynamodb"
        syntheticz = Syntheticz(
            service=SyntheticzServiceDetails(name="service-portal-state", version=__version__),
            status=SyntheticzStatus.UP,
            external_systems={dynamodb: SyntheticzExternalSystem(status=SyntheticzStatus.UP)},
        )

        with tracer.start_as_current_span("syntheticz-dynamodb") as span:
            span.set_attribute("syntheticz", True)  # noqa: FBT003 ignore boolean-positional-value-in-call here
            try:
                await self._client.describe_table(TableName=self._table_name)
            except Exception:
                # We explicitely use broad exception here, as we want to be sure that any
                # exception is returning DOWN status, even if we don't know the exact reason.
                logger.exception("Failed to access dynamodb table")
                syntheticz.status = SyntheticzStatus.DOWN
                syntheticz.external_systems[dynamodb].status = SyntheticzStatus.DOWN

        return syntheticz


# FastAPI dependency injection function and definitions
async def get_syntheticz_service(
    client: DynamoDBClientDep,
    settings: SettingsDep,
) -> SyntheticzService:
    return SyntheticzService(client, settings)


SyntheticzServiceDep = Annotated[SyntheticzService, Depends(get_syntheticz_service)]
