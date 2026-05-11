import logging

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import AiobotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    LogRecordExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter

from fastapi import FastAPI

from app.settings import Settings, get_settings

_resource = Resource.create({"service.name": "service-portal-state"})


def _get_providers(settings: Settings) -> tuple[LoggerProvider | None, TracerProvider | None]:
    if settings.otel_sdk_disabled:
        return None, None

    # Log provider can be used together with logging instrumentation to send logs to the OTEL
    # configured exporter in the correct OTEL format
    log_provider = LoggerProvider(resource=_resource)
    set_logger_provider(log_provider)

    # Trace provider
    trace_provider = TracerProvider(resource=_resource)
    trace.set_tracer_provider(trace_provider)

    return log_provider, trace_provider


def _get_exporters(
    settings: Settings,
) -> tuple[
    list[LogRecordExporter],
    list[SpanExporter],
    list[MetricExporter],
]:
    if settings.otel_sdk_disabled:
        return [], [], []

    metric_exporters = []
    logs_exporters = []
    span_exporters = []

    # OTLP exporters
    if settings.otel_enable_otlp_exporter:
        # Tracing OTLP exporter
        if "otlp" in settings.otel_trace_exporters:
            span_exporters.append(
                OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    headers=settings.otel_exporter_otlp_headers,
                    insecure=settings.otel_exporter_otlp_insecure,
                )
            )

        # Metrics OTLP exporter
        if "otlp" in settings.otel_metrics_exporters:
            metric_exporters.append(
                OTLPMetricExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    headers=settings.otel_exporter_otlp_headers,
                    insecure=settings.otel_exporter_otlp_insecure,
                )
            )

        # Logs OTLP exporter
        if "otlp" in settings.otel_logging_exporters:
            logs_exporters.append(
                OTLPLogExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    headers=settings.otel_exporter_otlp_headers,
                    insecure=settings.otel_exporter_otlp_insecure,
                )
            )

    if settings.otel_enable_console_exporter:
        if "console" in settings.otel_trace_exporters:
            span_exporters.append(ConsoleSpanExporter())
        if "console" in settings.otel_metrics_exporters:
            metric_exporters.append(ConsoleMetricExporter())
        if "console" in settings.otel_logging_exporters:
            logs_exporters.append(ConsoleLogRecordExporter())

    return logs_exporters, span_exporters, metric_exporters


def _setup_log_processors(
    provider: LoggerProvider | None,
    exporters: list[LogRecordExporter],
) -> None:
    if provider is None:
        return

    for exporter in exporters:
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))


def _setup_span_processors(
    provider: TracerProvider | None,
    exporters: list[SpanExporter],
) -> None:
    if provider is None:
        return

    for exporter in exporters:
        provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_metrics(settings: Settings, exporters: list[MetricExporter]) -> MeterProvider | None:
    if settings.otel_sdk_disabled or not settings.otel_enable_metrics:
        return None

    # The periodic exporter can be configured via environment variable:
    # OTEL_METRIC_EXPORT_INTERVAL [ms] => default to 60'000
    # OTEL_METRIC_EXPORT_TIMEOUT [ms] => default to 30'000
    metric_readers = [PeriodicExportingMetricReader(exporter) for exporter in exporters]

    meter_provider = MeterProvider(
        metric_readers=metric_readers,
        resource=_resource,
    )
    metrics.set_meter_provider(meter_provider)

    return meter_provider


def initialize_instrumentation(settings: Settings, app: FastAPI) -> None:
    if settings.otel_sdk_disabled:
        return

    # Setup tracing instrumentation
    if settings.otel_enable_boto:
        AiobotocoreInstrumentor().instrument()
    if settings.otel_enable_fastapi:
        FastAPIInstrumentor.instrument_app(app)


def shutdown_otel(settings: Settings) -> None:
    """Flush and shutdown OTEL providers/processors on application shutdown."""
    if settings.otel_sdk_disabled:
        return

    if trace_provider is not None:
        trace_provider.shutdown()

    if log_provider is not None:
        log_provider.shutdown()

    if meter_provider is not None:
        meter_provider.shutdown()


# ------------------------------------------------------------------------------
# NOTE: Import-time setup is intentional.
#
# This allows uvicorn's logging.dictConfig() to resolve:
#
#   handlers:
#     otel:
#       (): app.otel.get_otel_handler
#
# At that point, get_otel_handler() must be importable and must already have access
# to an initialized LoggerProvider.

settings = get_settings()

log_provider, trace_provider = _get_providers(settings)

log_exporters, span_exporters, metric_exporters = _get_exporters(settings)

_setup_log_processors(log_provider, log_exporters)
_setup_span_processors(trace_provider, span_exporters)

meter_provider = _setup_metrics(settings, metric_exporters)


def get_otel_handler() -> logging.Handler:
    """Get the OTEL logging Handler"""
    if settings.otel_sdk_disabled:
        raise ValueError(
            "Cannot use OTEL handler in logging configuration when OTEL_SDK_DISABLE is true"
        )
    if log_provider is None:
        raise ValueError("OTEL log provider is not available")

    return LoggingHandler(logger_provider=log_provider)
