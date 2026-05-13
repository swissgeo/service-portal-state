import json
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Annotated, Any

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.config import Config
from types_aiobotocore_dynamodb import DynamoDBClient

from fastapi import Depends, Request
from pydantic import BaseModel, ValidationError

from app.settings import SettingsDep

_serializer = TypeSerializer()
_deserializer = TypeDeserializer()


async def get_dynamodb_client(
    request: Request, settings: SettingsDep
) -> AsyncGenerator[DynamoDBClient]:
    """
    Returns a database client dependency based on configuration.
    """

    # Get the session from app state
    session = request.app.state.dynamodb_session

    # Create a client for this request using the shared session
    async with session.client(
        "dynamodb",
        endpoint_url=settings.aws_endpoint_url,
        config=Config(
            connect_timeout=5,
            read_timeout=10,
            # See https://docs.aws.amazon.com/boto3/latest/guide/retries.html for detail
            retries={
                "mode": "standard",
                "total_max_attempts": 3,
            },
        ),
    ) as dynamodb_client:
        dynamodb_client: DynamoDBClient
        yield dynamodb_client


# FastAPI dependency injection function and definitions
DynamoDBClientDep = Annotated[DynamoDBClient, Depends(get_dynamodb_client)]


def dynamodb_to_basemodel[T: BaseModel](
    basemodel: type[T],
    dynamodb_data: dict[str, Any],
) -> T:
    """Convert a DynamoDB item into a Pydantic BaseModel instance."""
    try:
        return basemodel.model_validate(
            {key: _deserializer.deserialize(value) for key, value in dynamodb_data.items()},
            by_name=True,
        )
    except ValidationError as e:  # pragma: no cover
        raise ValueError(f"Error validating data against {basemodel.__name__}: {e}") from e


def basemodel_to_dynamodb(basemodel: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic BaseModel instance into a DynamoDB item dict."""
    # Serialize to JSON and back with Decimal so TypeSerializer receives the correct numeric type
    as_dict = json.loads(
        basemodel.model_dump_json(by_alias=True),
        parse_float=Decimal,
        parse_int=Decimal,
    )
    return {
        key: _serializer.serialize(value) for key, value in as_dict.items() if value is not None
    }


def get_key(
    primary_key_name: str,
    primary_key_value: str | int,
    sort_key_name: str | None = None,
    sort_key_value: str | int | None = None,
) -> dict:
    """Generate a DynamoDB key dict for get/update/delete operations."""
    key = {primary_key_name: _serializer.serialize(primary_key_value)}

    if sort_key_name:
        if sort_key_value is None:
            raise ValueError("No value provided for sort key")
        key[sort_key_name] = _serializer.serialize(sort_key_value)

    return key
