"""
apps/lib/otel.py
----------------
OpenTelemetry tracer and meter singletons for DocuBricks apps.

If ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, traces and metrics are exported to
the configured collector endpoint using OTLP/gRPC.  If the variable is absent
or empty, the SDK is configured with no-op exporters so all instrumentation
calls succeed silently — apps do not need to guard every tracing call.

Pre-created instruments
~~~~~~~~~~~~~~~~~~~~~~~
``docs_uploaded``          Counter (unit="1")
``processing_duration``    Histogram (unit="s")
``extraction_confidence``  Histogram (unit="1")
``review_queue_depth``     UpDownCounter (unit="1")
``genie_latency``          Histogram (unit="s")

Usage in apps::

    from lib.otel import tracer, docs_uploaded, genie_latency

    with tracer.start_as_current_span("upload"):
        docs_uploaded.add(1, {"tenant_id": tid, "vertical": v})
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import streamlit as st

# OpenTelemetry core
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from opentelemetry.metrics import Counter, Histogram, UpDownCounter
    from opentelemetry.trace import Tracer


# ---------------------------------------------------------------------------
# Resource (shared by traces + metrics)
# ---------------------------------------------------------------------------

_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "docubricks")
_RESOURCE = Resource.create({"service.name": _SERVICE_NAME})


# ---------------------------------------------------------------------------
# Cached OTel initialisation
# ---------------------------------------------------------------------------

@st.cache_resource
def _init_otel() -> tuple:
    """
    Initialise TracerProvider and MeterProvider.

    Returns a tuple of (tracer_provider, meter_provider).  Subsequent calls
    return the same objects from the Streamlit resource cache.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()

    if endpoint:
        # ── Real exporters ──────────────────────────────────────────────────
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)

        tracer_provider = TracerProvider(resource=_RESOURCE)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60_000)
        meter_provider = MeterProvider(resource=_RESOURCE, metric_readers=[reader])
    else:
        # ── No-op mode: use SDK providers with no exporters ─────────────────
        tracer_provider = TracerProvider(resource=_RESOURCE)
        meter_provider = MeterProvider(resource=_RESOURCE)

    # Register globally so third-party libraries pick them up automatically
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    return tracer_provider, meter_provider


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

# Trigger initialisation at import time (safe to call multiple times due to cache)
_tracer_provider, _meter_provider = _init_otel()

#: OpenTelemetry tracer — use with ``tracer.start_as_current_span(...)``
tracer: "Tracer" = trace.get_tracer("docubricks")

_meter = metrics.get_meter("docubricks")

# ---------------------------------------------------------------------------
# Pre-created metric instruments
# ---------------------------------------------------------------------------

#: Number of documents successfully uploaded to the volume
docs_uploaded: "Counter" = _meter.create_counter(
    name="docs_uploaded",
    description="Number of documents uploaded",
    unit="1",
)

#: End-to-end processing duration from upload to terminal state
processing_duration: "Histogram" = _meter.create_histogram(
    name="processing_duration",
    description="End-to-end document processing duration",
    unit="s",
)

#: Extraction confidence score recorded per document
extraction_confidence: "Histogram" = _meter.create_histogram(
    name="extraction_confidence",
    description="Extraction confidence score per document",
    unit="1",
)

#: Current depth of the human review queue (signed — can decrease on resolution)
review_queue_depth: "UpDownCounter" = _meter.create_up_down_counter(
    name="review_queue_depth",
    description="Current number of items in the review queue",
    unit="1",
)

#: Latency of Genie Conversation API calls
genie_latency: "Histogram" = _meter.create_histogram(
    name="genie_latency",
    description="Latency of Genie conversation API calls",
    unit="s",
)
