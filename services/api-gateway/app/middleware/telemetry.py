from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import Settings


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """Initialise OpenTelemetry tracing and auto-instrument the FastAPI app.

    Sends spans via OTLP/HTTP to Jaeger (or any OTLP-compatible collector).
    No-op when ``otel_enabled`` is False — useful in unit tests.
    """
    if not settings.otel_enabled:
        return

    resource = Resource(attributes={SERVICE_NAME: settings.otel_service_name})

    sampler = ParentBased(root=TraceIdRatioBased(settings.otel_sample_rate))

    exporter = OTLPSpanExporter(
        endpoint=f"{settings.otel_otlp_endpoint}/v1/traces",
    )

    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="/health,/ready",  # skip probe noise from traces
    )


def shutdown_tracing() -> None:
    """Flush and shut down the global TracerProvider."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
