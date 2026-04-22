import json
from typing import Any

import pytest

from app.core.hashing import canonical_hash_bytes_96


# ---------------------------------------------------------
# 1. Canonicality test (same JSON different formatting → same hash)
# ---------------------------------------------------------
@pytest.mark.parametrize(
    ("left", "right"),
    [
        # simple key order difference
        (
            {"a": 1, "b": 2},
            {"b": 2, "a": 1},
        ),
        # nested objects
        (
            {"user": {"id": 1, "name": "alice"}, "active": True},
            {"active": True, "user": {"name": "alice", "id": 1}},
        ),
        # lists + nested dicts
        (
            {"items": [1, 2, 3], "meta": {"x": 10, "y": 20}},
            {"meta": {"y": 20, "x": 10}, "items": [1, 2, 3]},
        ),
        # deep nesting
        (
            {"a": {"b": {"c": {"d": 123}}}, "z": [1, 2, 3]},
            {"z": [1, 2, 3], "a": {"b": {"c": {"d": 123}}}},
        ),
        # mixed types
        (
            {"flag": True, "count": 0, "name": "test", "data": None},
            {"name": "test", "data": None, "count": 0, "flag": True},
        ),
    ],
)
def test_canonicality(left: Any, right: Any):
    raw_left = json.dumps(left).encode()
    raw_right = json.dumps(right).encode()

    full_left, short_left = canonical_hash_bytes_96(raw_left)
    full_right, short_right = canonical_hash_bytes_96(raw_right)

    assert full_left == full_right
    assert short_left == short_right


# ---------------------------------------------------------
# 2. Order sensitivity for lists
# ---------------------------------------------------------
def test_list_order_affects_hash():
    obj1 = {"items": [1, 2, 3]}
    obj2 = {"items": [3, 2, 1]}

    raw1 = json.dumps(obj1).encode()
    raw2 = json.dumps(obj2).encode()

    full1, short1 = canonical_hash_bytes_96(raw1)
    full2, short2 = canonical_hash_bytes_96(raw2)

    assert full1 != full2
    assert short1 != short2


# ---------------------------------------------------------
# 3. Short hash length (96 bits = 12 bytes = base64 ~16 chars)
# ---------------------------------------------------------
def test_short_hash_length():
    obj = {"a": 1, "b": 2}

    raw = json.dumps(obj).encode()

    _, short = canonical_hash_bytes_96(raw)

    # 96 bits = 12 bytes
    # base64 encoding of 12 bytes = 16 characters (no padding removed)
    assert len(short) == 16
