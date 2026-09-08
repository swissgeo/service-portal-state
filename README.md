# service-portal-state

| Branch  | Status    |
|---------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiMndndVlNMWc1dUZOK09mT1VYOHh0MlpNbkI1YjJvYmJ6THMxMEd6Q0N4UWkybmIwN2FqNzFDWDArREhoZmxDVDVWVlNLRVNyc1lvRUg1UGZKN3p2L0trPSIsIml2UGFyYW1ldGVyU3BlYyI6ImwxV2pzTDhhOU9xdVNJNWIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) [![codecov](https://codecov.io/github/swissgeo/service-portal-state/graph/badge.svg?token=07AV3ADXP1)](https://codecov.io/github/swissgeo/service-portal-state) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiMndndVlNMWc1dUZOK09mT1VYOHh0MlpNbkI1YjJvYmJ6THMxMEd6Q0N4UWkybmIwN2FqNzFDWDArREhoZmxDVDVWVlNLRVNyc1lvRUg1UGZKN3p2L0trPSIsIml2UGFyYW1ldGVyU3BlYyI6ImwxV2pzTDhhOU9xdVNJNWIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) [![codecov](https://codecov.io/gh/swissgeo/service-portal-state/branch/main/graph/badge.svg)](https://app.codecov.io/gh/swissgeo/service-portal-state/tree/main) |

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
- [Synthetic checks](#synthetic-checks)
- [Observability](#observability)
  - [Metrics](#metrics)
    - [Custom metrics](#custom-metrics)
    - [FastAPI auto-instrumentation metrics](#fastapi-auto-instrumentation-metrics)
  - [Logging implementation](#logging-implementation)
  - [Local OTEL testing](#local-otel-testing)
  - [Viewing custom metrics in Prometheus](#viewing-custom-metrics-in-prometheus)

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

Then run the moto-server (used for DynamoDB) and OTEL dependencies

```bash
make docker-compose-up
```

Then run the server from a separate terminal

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

## Synthetic checks

The service exposes a `GET /api/wps/v1/state/syntheticz` endpoint, used by the platform
monitoring agent to black-box check the service and its external dependencies. It follows the
[Synthetic checks in SWISSGEO](https://swissgeoplatform.atlassian.net/wiki/spaces/GEOIN/pages/826769409/Synthetic+checks+in+SWISSGEO)
guideline.

- `200` when the service and all external systems are healthy
- `500` when any external system is unhealthy; the body identifies which one

Example response:

```json
{
  "service": {
    "name": "service-portal-state",
    "version": "v0.1.0"
  },
  "status": "UP",
  "external_systems": {
    "dynamodb": {
      "status": "UP"
    }
  }
}
```

The response is served with `Cache-Control: no-store` so that CloudFront never returns a cached
check result.

This endpoint must not be used for kubernetes probes, use `/checker` for those.

### Check scope and limitations

The only external system of this service is the DynamoDB state table. It is checked with a
`DescribeTable` call, which is read-only and therefore leaves no state behind, making the check
idempotent and free of side effects.

The limitation of this approach is that `DescribeTable` is served by the DynamoDB control plane:
it proves that the table exists and that the service can reach and authenticate against DynamoDB,
but it does not exercise the data plane (`GetItem`/`PutItem`). A data plane read of a well-known
item would be a deeper check, but it would require a dedicated item to be provisioned and kept in
the table. A write-based smoke test is deliberately not implemented, as it could not be made
idempotent without deleting the written item afterwards.

## Observability

The service supports OpenTelemetry logging, tracing, and metrics.

### Metrics

#### Custom metrics

| Metric name | Type | Unit | Description |
|---|---|---|---|
| `swissgeo.service_portal_state.collisions` | Counter | `{collision}` | Counts hash collisions detected when two different state payloads produce the same short ID. Incremented by 1 on a real collision, and by 0 on a same-ID / same-hash hit (to ensure the metric is always reported). |

This metric has no additional attributes beyond the default OTEL resource attributes (e.g.
`service.name`).

In Prometheus the counter becomes `swissgeo_service_portal_state_collisions_total` (dots replaced
by underscores, `_total` suffix added automatically).

#### FastAPI auto-instrumentation metrics

The `FastAPIInstrumentor` (backed by `opentelemetry-instrumentation-asgi`) emits the following
metrics automatically for every HTTP request. The default semantic-convention mode (`DEFAULT`) uses
the **old** HTTP semconv attribute names.

| Metric name | Type | Unit | Description |
|---|---|---|---|
| `http.server.request.duration` | Histogram | `s` | Duration of inbound HTTP requests |
| `http.server.request.body.size` | Histogram | `By` | Size of HTTP request messages (compressed) |
| `http.server.response.body.size` | Histogram | `By` | Size of HTTP response messages (compressed) |
| `http.server.active_requests` | UpDownCounter | `{request}` | Number of currently in-flight HTTP requests |

Attributes attached to `http.server.request.duration`, `http.server.request.body.size`, and
`http.server.response.body.size`:

| Attribute | Example | Description |
|---|---|---|
| `url.scheme` | `http` | URL scheme |
| `network.protocol.version` | `1.1` | Network protocol version |
| `http.request.method` | `GET` | HTTP request method |
| `http.route` | `/` or `/{state_id}` | HTTP route |
| `http.response.status_code` | `200` | HTTP response status code |


Attributes attached to `http.server.active_requests`:

| Attribute | Example |
|---|---|
| `http.request.method` | `GET` |
| `url.scheme` | `http` |

> [!NOTE]
> The metrics above are from the new semantic convention for HTTP. They need to be enabled by setting `OTEL_SEMCONV_STABILITY_OPT_IN=http` in your environment. Use
> `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup` to emit both old and new metrics simultaneously
> during a migration.

In production deployments, telemetry can be exported using the configured OTLP exporters,
typically to an OpenTelemetry Collector or any OTLP-compatible observability platform. Only the OTLP
exportert is currently implemented by the application configuration layer.

By default, local development with the FastAPI dev server (make serve) runs with
OpenTelemetry disabled and uses standard Python console logging for a simpler and more
readable developer experience.

See [OpenTelemetry Python Instrumentation documentation](https://opentelemetry.io/docs/languages/python/instrumentation)

for more information about adding tracing and metrics inside the application code.

### Logging implementation

The application uses the OpenTelemetry `LoggerProvider` directly to export logs.

> [!WARNING]
> The deprecated `opentelemetry-instrumentation-logging` package is intentionally not
> used, as `LoggerProvider` already associates logs with the active trace/span context and
> provides native structured OTEL log exporting.

### Local OTEL testing

To test the full OTEL configuration locally (logs, traces, and metrics exported through
OpenTelemetry), use the provided OTEL environment configuration and run the application
with Docker:

1. Start the local otel collector

    ```bash
    make start-otel
    ```

2. In a new shell start the application

    ```bash
    cp .env.otel .env
    make dockerrun
    ```

This configuration enables the OTLP exporters and sends telemetry to the local configured
OpenTelemetry collector endpoint created via `make start-otel`.

Then you will see OTEL logs and metrics in the first shell in which you started `make start-otel` and
you can see the full trace using `jaeger` trace explorer at http://localhost:16686

### Viewing custom metrics in Prometheus

The local stack forwards OTEL metrics from the collector to Prometheus via OTLP. Once the stack is
running, open the Prometheus UI at http://localhost:9090.

Custom application metrics follow the OpenTelemetry naming convention and are automatically
translated to Prometheus metric names by replacing `.` with `_`. For example, the
`swissgeo.service_portal_state.collisions` counter becomes `swissgeo_service_portal_state_collisions_total` in
Prometheus (Prometheus appends `_total` to all counter metrics).

To query it:

1. Open http://localhost:9090 in your browser.
2. Click the **"Metrics Explorer"** icon (or type directly in the search bar).
3. Enter the metric name in the expression field:

    ```promql
    service_portal_state_collisions_total
    ```

4. Click **"Execute"** to see the current value, or switch to the **"Graph"** tab to visualize it
   over time.

To filter by a specific label (e.g. only collisions on a given endpoint):

```promql
swissgeo_service_portal_state_collisions_total{http_route="/api/state/{uuid}"}
```

To see the per-second rate over the last 5 minutes:

```promql
rate(swissgeo_service_portal_state_collisions_total[5m])
```

> [!TIP]
> If the metric does not appear, make sure you have triggered at least one collision (Prometheus only
> exposes a metric after it has been observed at least once) and that the OTLP pipeline is healthy
> (check the otel-collector logs for export errors).
