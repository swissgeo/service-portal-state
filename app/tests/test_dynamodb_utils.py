from typing import Any

from pydantic import BaseModel, Field

import pytest

from app.core.db import (
    basemodel_to_dynamodb,
    dynamodb_to_basemodel,
    get_key,
)

# ------------------------------------------------------------------
# Test models
# ------------------------------------------------------------------


class UserModel(BaseModel):
    id: int
    name: str
    active: bool
    score: float
    items: list[int]
    metadata: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# dynamodb_to_basemodel
# ------------------------------------------------------------------


def test_dynamodb_to_basemodel_full() -> None:
    dynamodb_data: dict[str, Any] = {
        "id": {"N": "1"},
        "name": {"S": "John"},
        "active": {"BOOL": True},
        "score": {"N": "10.5"},
        "items": {"L": [{"N": "1"}, {"N": "2"}]},
        "metadata": {"M": {"key": {"S": "value"}}},
    }

    result: UserModel = dynamodb_to_basemodel(UserModel, dynamodb_data)

    assert isinstance(result, UserModel)
    assert result.id == 1
    assert result.name == "John"
    assert result.active is True
    assert result.score == 10.5
    assert result.items == [1, 2]
    assert result.metadata == {"key": "value"}


def test_dynamodb_to_basemodel_invalid() -> None:
    bad_data: dict[str, Any] = {
        "id": {"S": "not-an-int"},  # should fail validation
    }

    with pytest.raises(
        ValueError, match="Error validating data against UserModel: 5 validation errors"
    ):
        dynamodb_to_basemodel(UserModel, bad_data)


# ------------------------------------------------------------------
# basemodel_to_dynamodb
# ------------------------------------------------------------------


def test_basemodel_to_dynamodb_full() -> None:
    model: UserModel = UserModel(
        id=1,
        name="John",
        active=True,
        score=10.5,
        items=[1, 2],
        metadata={"key": "value"},
    )

    result: dict[str, Any] = basemodel_to_dynamodb(model)

    assert result["id"] == {"N": "1"}
    assert result["name"] == {"S": "John"}
    assert result["active"] == {"BOOL": True}
    assert result["score"] == {"N": "10.5"}
    assert result["items"]["L"] == [{"N": "1"}, {"N": "2"}]
    assert result["metadata"]["M"]["key"] == {"S": "value"}


def test_basemodel_to_dynamodb_excludes_none() -> None:
    class Model(BaseModel):
        a: int
        b: str | None = None

    model: Model = Model(a=1)

    result: dict[str, Any] = basemodel_to_dynamodb(model)

    assert "a" in result
    assert "b" not in result


# ------------------------------------------------------------------
# get_key
# ------------------------------------------------------------------


def test_get_key_string_pk() -> None:
    result: dict = get_key("id", "abc")

    assert result == {"id": {"S": "abc"}}


def test_get_key_int_pk() -> None:
    result: dict = get_key("id", 123)

    assert result == {"id": {"N": "123"}}


def test_get_key_with_sort_key_string() -> None:
    result: dict = get_key("pk", "a", "sk", "b")

    assert result == {
        "pk": {"S": "a"},
        "sk": {"S": "b"},
    }


def test_get_key_with_sort_key_int() -> None:
    result: dict = get_key("pk", 1, "sk", 2)

    assert result == {
        "pk": {"N": "1"},
        "sk": {"N": "2"},
    }


def test_get_key_missing_sort_value() -> None:
    with pytest.raises(ValueError, match="No value provided for sort key"):
        get_key("pk", "a", "sk", None)


def test_get_key_invalid_pk_type() -> None:
    with pytest.raises(TypeError, match="Float types are not supported"):
        get_key("pk", 1.5)  # ty:ignore[invalid-argument-type]


def test_get_key_invalid_sk_type() -> None:
    with pytest.raises(TypeError, match="Float types are not supported"):
        get_key("pk", "a", "sk", 1.5)  # ty:ignore[invalid-argument-type]


# ------------------------------------------------------------------
# Edge cases for transformation functions indirectly
# ------------------------------------------------------------------


def test_nested_structures_roundtrip() -> None:
    class NestedModel(BaseModel):
        data: dict[str, Any]

    model: NestedModel = NestedModel(
        data={
            "list": [1, {"nested": "value"}],
            "bool": True,
        }
    )

    dynamodb: dict[str, Any] = basemodel_to_dynamodb(model)
    result: NestedModel = dynamodb_to_basemodel(NestedModel, dynamodb)

    assert result == model
