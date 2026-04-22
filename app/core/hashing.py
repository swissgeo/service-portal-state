import base64
import hashlib

import orjson


def canonical_hash_bytes_96(raw_body: bytes) -> tuple[str, str]:
    """
    Parse incoming JSON bytes, re-serialize canonically, hash with SHA-256,
    truncate to 96 bits, encode URL-safe base64 without padding.

    Returns:
        (full_hex_sha256, truncated_96bit_base64url)
    """
    obj = orjson.loads(raw_body)

    canonical = orjson.dumps(
        obj,
        option=orjson.OPT_SORT_KEYS,
    )
    full_hash = hashlib.sha256(canonical).digest()

    truncated = base64.urlsafe_b64encode(full_hash[:12]).rstrip(b"=").decode("ascii")

    return full_hash.hex(), truncated
