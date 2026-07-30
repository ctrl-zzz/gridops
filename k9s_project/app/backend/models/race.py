from datetime import datetime

from pydantic import BaseModel


class PodiumPosition(BaseModel):
    position: int
    driver_number: int
    driver_name: str
    team_name: str
    laps: int | None = None
    gap_to_leader: float | str | None = None


class Race(BaseModel):
    session_key: int
    year: int
    circuit: str
    location: str
    country: str
    date_start: datetime
    date_end: datetime
    podium: list[PodiumPosition]