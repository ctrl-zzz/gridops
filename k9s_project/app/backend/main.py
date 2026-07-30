from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.race import Race
from services.openf1 import get_latest_race


app = FastAPI(
    title="GridOps API",
    description="Formula One Operations Platform",
    version="0.1.0",
)


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


templates = Jinja2Templates(
    directory="templates",
)


@app.get(
    "/",
    include_in_schema=False,
)
async def homepage(request: Request):
    race = await get_latest_race()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "race": race,
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