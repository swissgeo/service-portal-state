# Synthetic check plugin

Reusable FastAPI plugin implementing the SWISSGEO
[synthetic check contract](https://swissgeoplatform.atlassian.net/wiki/spaces/GEOIN/pages/826769409/Synthetic+checks+in+SWISSGEO).

The package has no dependency on this service, it can be copied as-is into any FastAPI service.

## Usage

```python
from app.syntheticz import SyntheticError, setup_syntheticz


async def check(client: DynamoDBClientDep) -> list[str]:
    try:
        await client.describe_table(TableName="my-table")
    except ClientError as e:
        raise SyntheticError(failed={"dynamodb": str(e)}) from e
    return ["dynamodb"]


setup_syntheticz(app, check=check, version=__version__, tags=["Internal"])
```

## The check function

- It may be sync or async, and may declare FastAPI dependencies in its signature (it is wired
  into the route as a real dependency).
- It returns the healthy external system names, or `None` when there is none to report.
- It raises `SyntheticError` when one or more external systems are unhealthy. The failed systems
  must be provided, either as a list of names or as a `{name: reason}` mapping. The reason is
  logged only, it is never sent to the client. A `SyntheticError` without a failed system raises
  `ValueError`, as it would carry no actionable information.
- It must be idempotent and free of side effects.

## Responses

`200` when the check function returns, `500` when it raises `SyntheticError`:

```json
{
  "service": { "name": "my-service", "version": "v1.2.0" },
  "status": "DOWN",
  "external_systems": { "dynamodb": { "status": "DOWN" } }
}
```

Both responses carry `Cache-Control: no-store`.

## Configuration

| Argument | Default | Description |
|---|---|---|
| `name` | `SERVICE_NAME` env var, else `unknown-service` | Reported as `service.name` |
| `version` | required | Reported as `service.version` |
| `path` | `/syntheticz` | Route path of the endpoint |
| `tags` | none | OpenAPI tags for the route |

`path` is **relative to the application `root_path`**, which FastAPI prepends. With
`root_path="/api/wps/v1/state"` the default is already served at
`/api/wps/v1/state/syntheticz`; passing that full path here would serve it at
`/api/wps/v1/state/api/wps/v1/state/syntheticz` instead.

## Notes

- The request span is marked with the `synthetic=true` OTEL attribute before the check runs.
- Register the plugin **before** any router with a catch-all route such as `GET /{id}`, which
  would otherwise shadow `GET /syntheticz`.
- This endpoint must not be used for kubernetes probes.
