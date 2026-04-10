# service-shortlink

| Branch  | Status    |
|---------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiS1BkNmk4OGdudUZZTW5tM0J1NDdsc3h2L1c3ZXR5d09lRTRCZm82Q2FHWHRHKzRoT2JHU1lmbEY5a3cremtCWVdMWHFEcEtSVVY1QTZOSUx3dnNUWGhJPSIsIml2UGFyYW1ldGVyU3BlYyI6IjVya0JjTnJPVFBtcmtpeXYiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiS1BkNmk4OGdudUZZTW5tM0J1NDdsc3h2L1c3ZXR5d09lRTRCZm82Q2FHWHRHKzRoT2JHU1lmbEY5a3cremtCWVdMWHFEcEtSVVY1QTZOSUx3dnNUWGhJPSIsIml2UGFyYW1ldGVyU3BlYyI6IjVya0JjTnJPVFBtcmtpeXYiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) |

Service shortlink is the new short URL backend service for SWISSGEO.

- [Development](#development)
  - [Dependencies](#dependencies)
  - [Setup](#setup)
  - [Linting and Formatting](#linting-and-formatting)
  - [Pre-Commit Hooks](#pre-commit-hooks)
  - [Updating Packages](#updating-packages)
  - [Testing](#testing)
- [OpenAPI](#openapi)

## Development

This service uses the [FastAPI](https://fastapi.tiangolo.com/) framework.

### Dependencies

Prerequisites on host for development and build:

- python version 3.14
- uv
- docker and docker compose

### Setup

To create and activate a virtual Python environment with all dependencies installed:

```bash
make setup
```

Then run the server

```bash
make serve
```

### Linting and Formatting

This project uses `ruff` as linter and formatter. It also uses `ty` as type checker.

To lint and type check use

```bash
make lint
```

To format

```bash
make format
```

### Pre-Commit Hooks

This project uses pre-commit hooks to lint and type-check before committing. Pre-commits hooks can
either be bypassed entirely with the `--no-verify` option (`git commit --no-verify ...`), or
individually using the `SKIP` environment variable (`SKIP=lint git commit ...`).

### Updating Packages

All packages used in production are pinned to a major version. Automatically updating these packages
will use the latest minor (or patch) version available. Packages used for development, on the other
hand, are not pinned unless they need to be used with a specific version of a production package
(for example, boto3-stubs for boto3).

To update the packages to the latest minor/compatible versions, run:

```bash
uv sync --upgrade
```

To see what major/incompatible releases would be available, run:

```bash
uv pip list --outdated
```

To update packages to a new major release, run:

```bash
uv add "fastapi[standard]~=v0.135"
```

### Testing

This project uses `pytest` for testing, to start the tests enter

```bash
make test
```

## OpenAPI

FastAPI automatically generates an OpenAPI schema, so each path operation should define its request
parameters and responses using `pydantic` models to ensure they are properly documented. To view the
OpenAPI documentation, run:

```bash
make serve
```

And then open:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger
- [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) for Redoc
