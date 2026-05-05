import logging

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import AiobotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
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


def _get_providers() -> tuple[LoggerProvider | None, TracerProvider | None]:
    if settings.otel_sdk_disable:
        return None, None

    # Log provider can be used together with logging instrumentation to send logs to the OTEL
    # configured exporter in the correct OTEL format
    log_provider = LoggerProvider(
        resource=Resource.create({"service.name": "service-portal-state"})
    )
    set_logger_provider(log_provider)

    # Trace provider
    trace_provider = TracerProvider(
        resource=Resource.create({"service.name": "service-portal-state"})
    )
    trace.set_tracer_provider(trace_provider)

    return log_provider, trace_provider


def _get_exporters(
    settings: Settings,
) -> tuple[
    list[LogRecordExporter],
    list[SpanExporter],
    list[MetricExporter],
]:
    if settings.otel_sdk_disable:
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
                )  # pragma: no-cover
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


# ------------------------------------------------------------------------------
# NOTE: The log Provider needs to be initialize at import time in order to allow
# uvicorn to use the get_otel_handler() from the logging.dictConfig().

settings = get_settings()

# Providers
log_provider, trace_provider = _get_providers()

# Exporters
logs_exporters, span_exporters, metric_exporters = _get_exporters(settings)

# Setup log processor and exporter
if log_provider:
    for exporter in logs_exporters:
        log_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

# Setup span processor and exporter (tracing)
if trace_provider:
    for exporter in span_exporters:
        trace_provider.add_span_processor(BatchSpanProcessor(exporter))

# Setup metrics
if settings.otel_enable_metrics and not settings.otel_sdk_disable:
    # The periodic exporter can be configured via environment variable:
    # OTEL_METRIC_EXPORT_INTERVAL [ms] => default to 60'000
    # OTEL_METRIC_EXPORT_TIMEOUT [ms] => default to 30'000
    metric_readers = [PeriodicExportingMetricReader(exporter) for exporter in metric_exporters]

    # Sets the global default meter provider
    metrics.set_meter_provider(MeterProvider(metric_readers=metric_readers))


def initialize_instrumentation(settings: Settings, app: FastAPI) -> None:
    if settings.otel_sdk_disable:
        return

    # Setup tracing instrumentation
    if settings.otel_enable_boto:
        AiobotocoreInstrumentor().instrument()
    if settings.otel_enable_fastapi:
        FastAPIInstrumentor.instrument_app(app)


def get_otel_handler() -> logging.Handler:
    """Get the OTEL logging Handler"""
    if settings.otel_sdk_disable:
        raise ValueError(
            "Cannot use OTEL handler in logging configuration when OTEL_SDK_DISABLE is true"
        )
    if log_provider is None:
        raise ValueError("OTEL log provider is not available")

    from opentelemetry.sdk._logs import LoggingHandler  # noqa: PLC0415

    return LoggingHandler(logger_provider=log_provider)
