from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import checker
from app.settings import get_settings
from app.version import __version__

app = FastAPI(
    title="Service Shortlink",
    summary="Create a short URL link",
    version=__version__,
    contact={"name": "swissgeo", "url": "https://www.swissgeo.ch"},
    license_info={
        "name": "BSD 3-Clause License",
        "identifier": "BSD-3-Clause",
    },
    openapi_tags=[{"name": "internal", "description": "Internal APIs not for external uses"}],
)

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=get_settings().cors_method,
    allow_headers=get_settings().cors_headers,
    max_age=get_settings().cors_max_age,
)

# Register routes
app.include_router(checker.router)
