"""Synthetic check plugin for FastAPI services.

Implements the SWISSGEO `syntheticz` contract, see
https://swissgeoplatform.atlassian.net/wiki/spaces/GEOIN/pages/826769409/Synthetic+checks+in+SWISSGEO

Usage:

    from app.syntheticz import SyntheticError, setup_syntheticz

    async def check() -> None:
        if not await my_db.reachable():
            raise SyntheticError(failed=["dynamodb"])

    setup_syntheticz(app, check=check, version=__version__)
"""

from app.syntheticz.exceptions import SyntheticError
from app.syntheticz.plugin import (
    SERVICE_NAME_ENV_VAR,
    SYNTHETIC_ATTRIBUTE,
    build_syntheticz_router,
    setup_syntheticz,
)
from app.syntheticz.schemas import (
    Syntheticz,
    SyntheticzExternalSystem,
    SyntheticzService,
    SyntheticzStatus,
)

__all__ = [
    "SERVICE_NAME_ENV_VAR",
    "SYNTHETIC_ATTRIBUTE",
    "SyntheticError",
    "Syntheticz",
    "SyntheticzExternalSystem",
    "SyntheticzService",
    "SyntheticzStatus",
    "build_syntheticz_router",
    "setup_syntheticz",
]
