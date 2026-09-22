from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


## Otel ##
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

## ##

from models.race import Race

from services.jolpica import (
    get_driver_championship_standings,
    get_latest_race,
    get_next_race,
)

from services.openf1 import get_starting_grid


T = TypeVar("T")


app = FastAPI(
    title="GridOps API",
    description="Formula One Operations Platform",
    version="0.1.0",
)

resource = Resource.create(
    {
        SERVICE_NAME: "gridops",
    }
)

tracer_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(
    OTLPSpanExporter()
)

tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter()
)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
)

metrics.set_meter_provider(meter_provider)

FastAPIInstrumentor.instrument_app(app)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


templates = Jinja2Templates(
    directory="templates",
)


async def optional_section(loader: Callable[[], Awaitable[T]]) -> T | None:
    try:
        return await loader()
    except HTTPException:
        return None


@app.get(
    "/",
    include_in_schema=False,
)
async def homepage(request: Request):
    race = await get_latest_race()
    next_race = await optional_section(get_next_race)
    starting_grid = await optional_section(
        lambda: get_starting_grid(next_race),
    )
    championship_standings = await optional_section(
        get_driver_championship_standings,
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "race": race,
            "next_race": next_race,
            "starting_grid": starting_grid,
            "championship_standings": championship_standings,
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "gridops",
    }


@app.get(
    "/race/latest",
    response_model=Race,
)
async def latest_race():
    return await get_latest_race()
