from collections.abc import AsyncGenerator
from typing import Annotated, Any, TypeVar

from botocore.config import Config
from types_aiobotocore_dynamodb import DynamoDBClient

from fastapi import Depends, Request
from pydantic import BaseModel, ValidationError

from app.settings import SettingsDep

T = TypeVar("T", bound=BaseModel)


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
            signature_version="s3v4",
        ),
    ) as dynamodb_client:
        dynamodb_client: DynamoDBClient
        yield dynamodb_client


# FastAPI dependency injection function and definitions
DynamoDBClientDep = Annotated[DynamoDBClient, Depends(get_dynamodb_client)]


async def dynamodb_to_basemodel[T: BaseModel](
    basemodel: type[T],
    dynamodb_data: dict[str, Any],
) -> T:
    """
    Convert a DynamoDB response body into Python data types and populate a Pydantic BaseModel.

    Args:
        basemodel (Type[BaseModel]): The Pydantic model class.
        dynamodb_data (Dict[str, Any]): The DynamoDB response.

    Returns:
        BaseModel: An instance of the Pydantic BaseModel filled with transformed data.
    """
    # Validate and return the BaseModel instance
    try:
        return basemodel.model_validate(
            {
                key: _transform_dynamodb_field_to_basemodel_field(value)
                for key, value in dynamodb_data.items()
            },
            by_name=True,
        )
    except ValidationError as e:  # pragma: no cover
        raise ValueError(f"Error validating data against {basemodel.__name__}: {e}") from e


async def basemodel_to_dynamodb(basemodel: BaseModel) -> dict[str, Any]:
    """
    Convert a Pydantic BaseModel instance into a DynamoDB-compatible dictionary.

    Args:
        basemodel (BaseModel): The Pydantic BaseModel instance.

    Returns:
        Dict[str, Any]: A dictionary formatted for DynamoDB.
    """
    # Convert the model to a dictionary and transform it
    return {
        key: _transform_basemodel_field_to_dynamodb_field(value)
        for key, value in basemodel.model_dump(mode="json", by_alias=True).items()
        if value is not None
    }


async def get_key(
    primary_key_name: str,
    primary_key_value: str | int,
    sort_key_name: str | None = None,
    sort_key_value: str | int | None = None,
) -> dict:
    """
    This function generates the key schema, i.e. which item to retrieve/update/delete etc.
    """
    key = {}
    if isinstance(primary_key_value, str):
        key[primary_key_name] = {"S": primary_key_value}
    elif isinstance(primary_key_value, int):
        key[primary_key_name] = {"N": str(primary_key_value)}
    else:
        raise TypeError(f"Unsupported type for partition key value: {type(primary_key_value)}")

    if sort_key_name:
        if not sort_key_value:
            raise ValueError("No value provided for sort key")

        if isinstance(sort_key_value, str):
            key[sort_key_name] = {"S": sort_key_value}
        elif isinstance(sort_key_value, int):
            key[sort_key_name] = {"N": sort_key_value}
        else:
            raise TypeError(f"Unsupported type for sort key value: {type(sort_key_value)}")

    return key


def _transform_basemodel_field_to_dynamodb_field(value: Any) -> Any:
    if isinstance(value, str):
        return {"S": value}  # String
    if isinstance(value, bool):
        return {"BOOL": value}  # Boolean
    if isinstance(value, (int, float)):
        return {"N": str(value)}  # Number
    # We don't support set because of the BaseModel dump above in json mode, using python mode will
    # solve the issue with set, but will have issues with tuple and datetime object
    # if isinstance(value, set):
    #     return {"SS": list(value)}
    if isinstance(value, list):
        return {"L": [_transform_basemodel_field_to_dynamodb_field(item) for item in value]}  # List
    if isinstance(value, dict):
        return {
            "M": {
                key: _transform_basemodel_field_to_dynamodb_field(val)
                for key, val in value.items()
                if val is not None
            }
        }  # Map

    raise TypeError(f"Unsupported type: {type(value)} for value: {value}")  # pragma: no cover


def _transform_dynamodb_field_to_basemodel_field(value: Any) -> Any:  # noqa: PLR0911
    if isinstance(value, dict):
        if "S" in value:
            return value["S"]  # String
        if "BOOL" in value:
            return value["BOOL"]  # Boolean
        if "N" in value:
            return (
                float(value["N"]) if "." in value["N"] else int(value["N"])
            )  # Number (integer or float)
        # We don't support set because of the BaseModel dump above in json mode, using python mode
        # will solve the issue with set, but will have issues with tuple and datetime object
        # if "SS" in value:
        #     return set(value["SS"]).difference({""})  # Set of Strings
        if "L" in value:
            return [
                _transform_dynamodb_field_to_basemodel_field(item) for item in value["L"]
            ]  # List
        if "M" in value:
            return {
                key: _transform_dynamodb_field_to_basemodel_field(val)
                for key, val in value["M"].items()
            }  # Nested Map

        return value  # pragma: no cover  In case of unexpected structure
    return value  # pragma: no cover  If it's not a dict, return it as is
