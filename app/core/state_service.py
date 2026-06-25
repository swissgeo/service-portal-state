import logging
from datetime import UTC, datetime
from typing import Annotated

from botocore.exceptions import ClientError
from opentelemetry import trace
from types_aiobotocore_dynamodb import DynamoDBClient

from fastapi import Depends

from app.core.db import DynamoDBClientDep, basemodel_to_dynamodb, dynamodb_to_basemodel, get_key
from app.core.metrics import increment_collision_meter
from app.schemas.db import DBStateItem
from app.schemas.state import StateId, StateItem
from app.settings import SettingsDep

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)


class StateService:
    def __init__(self, client: DynamoDBClient, settings: SettingsDep) -> None:
        self._client = client
        self._table_name = settings.aws_dynamodb_table_name

    async def save_app_state(self, state_id: StateId, full_hash: str, state: StateItem) -> bool:
        """Save the application state in the DB

        Args:
            state_id (str): state ID to save
            full_hash (str): state full hash
            state (StateItem): state object to save

        Returns:
            bool: True if the state was saved, False if a state with the same ID already exists

        Raises:
            ValueError: If a state with the same ID but different hash already exists (collision)
        """
        logger.debug("Saving state with id=%s and hash=%s into DynamoDB", state_id, full_hash)
        try:
            await self._client.put_item(
                TableName=self._table_name,
                Item=basemodel_to_dynamodb(
                    DBStateItem.from_state_item(
                        state_id=state_id, full_hash=full_hash, version=1, state=state
                    )
                ),
                ConditionExpression="attribute_not_exists(id)",
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info(
                    "State with id=%s already exists, checking for hash collision", state_id
                )
                await self._check_for_collision(state_id=state_id, full_hash=full_hash)

                return False

            logger.exception("Unexpected DB error while saving app state")  # pragma: no cover
            raise  # pragma: no cover

        return True

    async def get_app_state(self, state_id: str) -> DBStateItem | None:
        """Retrieve an application state

        Args:
            state_id (str): application state ID to retrieve

        Returns:
            tuple[StateItem, DBStateItem] | tuple[None, None]: State object and DB item if the
            state was found, None otherwise
        """
        logger.debug("Retrieving state with id=%s from DynamoDB", state_id)
        db_item = await self._get_db_item(state_id=state_id)
        if db_item is None:
            logger.info("State with id=%s not found", state_id)
            return None

        return db_item

    @tracer.start_as_current_span("update-last-accessed")
    async def update_last_accessed(self, db_item: DBStateItem) -> None:
        logger.debug("Updating last accessed for state with id=%s", db_item.id)
        db_item.last_accessed = datetime.now(tz=UTC)

        try:
            await self._client.put_item(
                TableName=self._table_name,
                Item=basemodel_to_dynamodb(db_item),
            )

        except ClientError:  # pragma: no cover
            logger.exception("Unexpected DB error while updating last accessed")
            raise

    async def _get_db_item(self, state_id: str) -> DBStateItem | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key=get_key(primary_key_name="id", primary_key_value=state_id),
        )

        if "Item" not in response:
            return None

        return dynamodb_to_basemodel(DBStateItem, response["Item"])

    async def _check_for_collision(self, state_id: str, full_hash: str) -> None:
        existing_item = await self._get_db_item(state_id=state_id)
        if existing_item is None:
            raise ValueError(
                f"State with id={state_id} already exists but could not be retrieved to check "
                "for collision"
            )  # pragma: no cover

        if existing_item.full_hash != full_hash:
            # When a collision happens, we need to analyze the collision and take measures.
            # In theory, we should never have collisions, but if we start to have collisions,
            # we need to take immediate measures. The metrics will help us monitor and alert
            # us when collisions occur.
            increment_collision_meter(1)
            logger.exception(
                "Collision detected for state_id=%s: existing hash=%s, new hash=%s",
                state_id,
                existing_item.full_hash,
                full_hash,
            )
            raise ValueError(f"Collision detected for id={state_id}")
        # In case there is no collision, we still need to increment the meter to 0 in order to
        # add a value to the meter, otherwise the meter will not record any values.
        increment_collision_meter(0)


# FastAPI dependency injection function and definitions
async def get_state_service(
    client: DynamoDBClientDep,
    settings: SettingsDep,
) -> StateService:
    return StateService(client, settings)


StateServiceDep = Annotated[StateService, Depends(get_state_service)]
