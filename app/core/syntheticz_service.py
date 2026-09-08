import logging
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from opentelemetry import trace
from types_aiobotocore_dynamodb import DynamoDBClient

from fastapi import Depends

from app.core.db import DynamoDBClientDep
from app.schemas.syntheticz import (
    Syntheticz,
    SyntheticzExternalSystem,
    SyntheticzService,
    SyntheticzStatus,
)
from app.settings import SettingsDep
from app.version import __version__

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

SERVICE_NAME = "service-portal-state"

# Attribute added to every OTEL signal emitted during a synthetic check, so that synthetic
# traffic can be filtered out of the regular service telemetry.
# See https://swissgeoplatform.atlassian.net/wiki/spaces/GEOIN/pages/826769409
SYNTHETIC_ATTRIBUTE = "synthetic"


class SyntheticzChecker:
    def __init__(self, client: DynamoDBClient, settings: SettingsDep) -> None:
        self._client = client
        self._table_name = settings.aws_dynamodb_table_name

    async def check(self) -> Syntheticz:
        """Run the synthetic check over all external systems.

        The check is read-only, it therefore leaves no state behind and is idempotent.

        Returns:
            Syntheticz: the check result, DOWN as soon as one external system is DOWN
        """
        external_systems = {"dynamodb": await self._check_dynamodb()}

        status = (
            SyntheticzStatus.UP
            if all(system.status is SyntheticzStatus.UP for system in external_systems.values())
            else SyntheticzStatus.DOWN
        )

        return Syntheticz(
            service=SyntheticzService(name=SERVICE_NAME, version=__version__),
            status=status,
            external_systems=external_systems,
        )

    async def _check_dynamodb(self) -> SyntheticzExternalSystem:
        """Check the DynamoDB state table with a cheap read-only metadata query."""
        with tracer.start_as_current_span("syntheticz-dynamodb") as span:
            span.set_attribute(SYNTHETIC_ATTRIBUTE, True)  # noqa: FBT003
            try:
                await self._client.describe_table(TableName=self._table_name)
            except ClientError, BotoCoreError:
                logger.exception(
                    "Synthetic check failed: DynamoDB table %s is not reachable",
                    self._table_name,
                    extra={SYNTHETIC_ATTRIBUTE: True},
                )
                return SyntheticzExternalSystem(status=SyntheticzStatus.DOWN)

        return SyntheticzExternalSystem(status=SyntheticzStatus.UP)


# FastAPI dependency injection function and definitions
async def get_syntheticz_checker(
    client: DynamoDBClientDep,
    settings: SettingsDep,
) -> SyntheticzChecker:
    return SyntheticzChecker(client, settings)


SyntheticzCheckerDep = Annotated[SyntheticzChecker, Depends(get_syntheticz_checker)]
