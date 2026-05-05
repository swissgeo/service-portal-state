# service-portal-state

| Branch  | Status    |
|---------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiMndndVlNMWc1dUZOK09mT1VYOHh0MlpNbkI1YjJvYmJ6THMxMEd6Q0N4UWkybmIwN2FqNzFDWDArREhoZmxDVDVWVlNLRVNyc1lvRUg1UGZKN3p2L0trPSIsIml2UGFyYW1ldGVyU3BlYyI6ImwxV2pzTDhhOU9xdVNJNWIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiMndndVlNMWc1dUZOK09mT1VYOHh0MlpNbkI1YjJvYmJ6THMxMEd6Q0N4UWkybmIwN2FqNzFDWDArREhoZmxDVDVWVlNLRVNyc1lvRUg1UGZKN3p2L0trPSIsIml2UGFyYW1ldGVyU3BlYyI6ImwxV2pzTDhhOU9xdVNJNWIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) |

Service portal state is the new shared application state backend service for SWISSGEO web-portal application.

- [Development](#development)
  - [Dependencies](#dependencies)
  - [Setup](#setup)
  - [Linting and Formatting](#linting-and-formatting)
  - [Pre-Commit Hooks](#pre-commit-hooks)
  - [Updating Packages](#updating-packages)
  - [Testing](#testing)
    - [DynamoDB mocking](#dynamodb-mocking)
- [OpenAPI](#openapi)
- [Observability](#observability)
  - [Testing OTEL configuration](#testing-otel-configuration)

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

Then run the moto-server (used for DynamoDB)

```bash
make start-moto
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

#### DynamoDB mocking

We use a Moto server to mock all DynamoDB calls, enabling simpler unit tests without needing to
manually mock each DynamoDB API interaction. For each test function, a new Moto server is started
on a random port to ensure proper test isolation and support concurrent execution.

Additionally, we provide two fixtures to directly mock DynamoDB `get_item` and `put_item` methods,
allowing us to test specific behaviors such as collisions:

- `mock_dynamodb_client_get_item`
- `mock_dynamodb_client_put_item`

> [!NOTE]
> We use a Moto server instead of the `@mock_aws` decorator because the decorator is not thread-safe.  
> Since `aioboto3` uses threads under the hood to provide asynchronous behavior on top of `boto3`,
> this can lead to unpredictable test behavior.  
> Running a dedicated Moto server per test ensures proper isolation and reliable concurrency.

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

## Observability

The service is setup with Opentelemetry logging, tracing and metrics.

By default when working locally with the FastAPI dev server (`make serve`), opentelemetry is disabled
and logs are nicely printed on the console.

See [Opentelemetry Python Instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
for more information on how to use tracing and metics in the application code.

### Testing OTEL configuration

If you want to test the OTEL configuration, where all logs, trace and metrics are sent via opentelemetry,
you can use the environment variable defined in `.env.otel` and start the application using docker

```bash
cp .env.otel .env
make dockerrun
```

Alternatively you can also test the configuration that uses both OTEL logs and standard python
console handler log in parallel.

```bash
cp .env.otel-console .env
make dockerrun
```
