from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import AiobotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from fastapi import FastAPI

from app.settings import Settings


def initialize(settings: Settings, app: FastAPI) -> None:  # pragma: no cover
    if settings.otel_sdk_disable:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "service-portal-state"}))
    trace.set_tracer_provider(provider)

    metric_exporter = None

    if settings.otel_enable_otlp_exporter:
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                headers=settings.otel_exporter_otlp_headers,
                insecure=settings.otel_exporter_otlp_insecure,
            )
        )
        provider.add_span_processor(span_processor)

        metric_exporter = OTLPMetricExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            headers=settings.otel_exporter_otlp_headers,
            insecure=settings.otel_exporter_otlp_insecure,
        )

    if settings.otel_enable_console_exporter:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        metric_exporter = ConsoleMetricExporter()

    if metric_exporter is not None:
        # Setup metrics
        # The periodic exporter can be configured via environment variable:
        # OTEL_METRIC_EXPORT_INTERVAL [ms] => default to 60'000
        # OTEL_METRIC_EXPORT_TIMEOUT [ms] => default to 30'000
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        metric_provider = MeterProvider(metric_readers=[metric_reader])

        # Sets the global default meter provider
        metrics.set_meter_provider(metric_provider)

    if settings.otel_enable_boto:
        AiobotocoreInstrumentor().instrument()
    if settings.otel_enable_logging:
        LoggingInstrumentor().instrument()
    if settings.otel_enable_fastapi:
        FastAPIInstrumentor.instrument_app(app)
