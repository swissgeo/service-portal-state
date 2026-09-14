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
from app.syntheticz.plugin import SYNTHETIC_ATTRIBUTE, build_syntheticz_router, setup_syntheticz
from app.syntheticz.schemas import (
    Syntheticz,
    SyntheticzExternalSystem,
    SyntheticzService,
    SyntheticzStatus,
)
from app.syntheticz.settings import SyntheticzSettings

__all__ = [
    "SYNTHETIC_ATTRIBUTE",
    "SyntheticError",
    "Syntheticz",
    "SyntheticzExternalSystem",
    "SyntheticzService",
    "SyntheticzSettings",
    "SyntheticzStatus",
    "build_syntheticz_router",
    "setup_syntheticz",
]
