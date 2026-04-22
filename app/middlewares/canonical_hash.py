import re
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.hashing import canonical_hash_bytes_96

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response


PATH_REGEX = re.compile(r"^/v\d+$")


class CanonicalHashMiddleware(BaseHTTPMiddleware):
    """Middleware to compute a canonical hash of the request body for POST /api/state requests.

    Compute the canonical request payload hash at middleware level, before the body is
    parsed into Pydantic models or passed to route handlers.

    Why this is done in middleware instead of inside each endpoint:

    - Performance: the raw request body is already available as bytes. Hashing here
      avoids the extra cost of creating Pydantic objects, calling `model_dump()`,
      and re-serializing Python data structures solely for hashing purposes.
    - Single read / single normalization: the payload is canonicalized and hashed
      once for the entire request lifecycle.
    - Separation of concerns: route handlers remain focused on business logic rather
      than infrastructure concerns such as fingerprinting or idempotency.
    - Reusability: the computed hash is stored in `request.state` and can be reused
      by any downstream component (routes, dependencies, logging, tracing, caching,
      deduplication, auditing, etc.).
    - Consistency: all JSON endpoints use the same hashing algorithm and canonical
      serialization rules.

    Starlette caches `request.body()`, so FastAPI and Pydantic can still read and
    parse the body normally afterward without consuming the stream twice.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only hash POST /api/state JSON requests
        if (
            request.method == "POST"
            and PATH_REGEX.fullmatch(request.url.path)
            and request.headers.get("content-type", "").startswith("application/json")
        ):
            raw = await request.body()

            # body() is cached by Starlette, downstream can read again safely
            request.state.payload_hash = canonical_hash_bytes_96(raw)

        return await call_next(request)
