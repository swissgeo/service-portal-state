import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api import checker
from app.settings import settings
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
    allow_origins=settings.cors_origins,
    allow_methods=settings.cors_method,
    allow_headers=settings.cors_headers,
    max_age=settings.cors_max_age,
)

# Register routes
app.include_router(checker.router)


# FastAPI only provides the openapi as json, so extend it to also provide the yaml output
@app.get("/openapi.yaml", include_in_schema=False)
def openapi_yaml() -> Response:
    return Response(
        yaml.dump(app.openapi(), sort_keys=False),
        media_type="application/yaml",
    )
