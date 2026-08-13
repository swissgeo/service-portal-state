from opentelemetry import metrics

# NOTES:
# - The meter name is used as scope.name field in Elastic Stack (Kibana)
# - Based on OTEL concept we use the module name as meter name
#   see https://opentelemetry.io/docs/concepts/instrumentation-scope/
# - The version should be incremented whenever the metric schema changes
meter = metrics.get_meter(__name__, version="1.0.0")


# NOTE: there is no standard metric for hash collisions, so I create a custom one
collision_meter = meter.create_counter(
    "swissgeo.service_portal_state.collisions",
    unit="{collision}",
    description="Hash collision counter",
)


def increment_collision_meter(increment: int) -> None:
    collision_meter.add(increment)
