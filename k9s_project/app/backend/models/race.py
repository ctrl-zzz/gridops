from datetime import datetime

from pydantic import BaseModel


class PodiumPosition(BaseModel):
    position: int
    driver_number: int
    driver_name: str
    team_name: str
    team_color: str
    laps: int | None = None
    gap_to_leader: float | str | None = None


class Race(BaseModel):
    year: int
    round: int
    race_name: str
    circuit: str
    location: str
    country: str
    date_start: datetime
    podium: list[PodiumPosition]


class NextRace(BaseModel):
    year: int
    round: int
    race_name: str
    circuit: str
    location: str
    country: str
    date_start: datetime
    local_start_label: str
    countdown_label: str


class GridDriver(BaseModel):
    position: int
    driver_number: int
    driver_name: str
    team_name: str
    team_color: str


class StartingGrid(BaseModel):
    year: int
    round: int
    title: str
    is_official: bool
    drivers: list[GridDriver]


class ChampionshipDriver(BaseModel):
    position: int
    driver_number: int
    driver_name: str
    team_name: str
    points: float
    points_label: str
    team_color: str


class ChampionshipStandings(BaseModel):
    year: int
    round: int
    drivers: list[ChampionshipDriver]