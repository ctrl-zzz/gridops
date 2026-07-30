from fastapi import FastAPI

from models.race import Race
from services.openf1 import get_latest_race

app = FastAPI(
    title="F1 Platform API",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.get("/race/latest", response_model=Race)
async def latest_race():
    return await get_latest_race()