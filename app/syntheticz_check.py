import logging

from botocore.exceptions import BotoCoreError, ClientError
from opentelemetry import trace

from app.core.db import DynamoDBClientDep
from app.settings import SettingsDep
from app.syntheticz import SYNTHETIC_ATTRIBUTE, SyntheticError

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

DYNAMODB = "dynamodb"


async def syntheticz_check(client: DynamoDBClientDep, settings: SettingsDep) -> list[str]:
    """Synthetic check of this service's external systems.

    The only external system is the DynamoDB state table, checked with a read-only DescribeTable
    call. It leaves no state behind, so the check is idempotent and free of side effects.

    Returns:
        list[str]: the healthy external systems

    Raises:
        SyntheticError: when the DynamoDB state table is not reachable
    """
    table_name = settings.aws_dynamodb_table_name

    with tracer.start_as_current_span("syntheticz-dynamodb") as span:
        span.set_attribute(SYNTHETIC_ATTRIBUTE, True)  # noqa: FBT003
        try:
            await client.describe_table(TableName=table_name)
        except (ClientError, BotoCoreError) as e:
            raise SyntheticError(
                failed={DYNAMODB: f"DynamoDB table {table_name} is not reachable: {e}"}
            ) from e

    return [DYNAMODB]
