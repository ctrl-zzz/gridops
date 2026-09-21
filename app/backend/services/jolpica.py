# services/jolpica.py

import os

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from constants.teams import team_color
from models.race import (
    ChampionshipDriver,
    ChampionshipStandings,
    NextRace,
    PodiumPosition,
    Race,
)


JOLPICA_BASE_URL = os.getenv(
    "JOLPICA_BASE_URL",
    "https://api.jolpi.ca/ergast/f1",
)

REQUEST_TIMEOUT = float(
    os.getenv("REQUEST_TIMEOUT", "10"),
)


def format_points(points: float) -> str:
    if points.is_integer():
        return str(int(points))

    return f"{points:g}"


def parse_race_datetime(
    date: str,
    time: str | None,
) -> datetime:
    value = f"{date}T{time or '00:00:00Z'}"

    return datetime.fromisoformat(
        value.replace("Z", "+00:00"),
    )


async def request_jolpica(
    client: httpx.AsyncClient,
    endpoint: str,
) -> dict:
    url = f"{JOLPICA_BASE_URL}/{endpoint}"

    try:
        response = await client.get(url)
        response.raise_for_status()

        return response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Jolpica request timed out",
        ) from exc

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {}

        raise HTTPException(
            status_code=502,
            detail="Jolpica API is unavailable",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Jolpica API is unavailable",
        ) from exc


async def get_latest_race() -> Race:
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        data = await request_jolpica(
            client,
            "current/last/results/",
        )

    races = (
        data
        .get("MRData", {})
        .get("RaceTable", {})
        .get("Races", [])
    )

    if not races:
        raise HTTPException(
            status_code=404,
            detail="No completed Formula 1 race found",
        )

    race = races[0]

    podium = []

    for result in race.get("Results", [])[:3]:
        driver = result["Driver"]
        constructor = result["Constructor"]

        podium.append(
            PodiumPosition(
                position=int(result["position"]),
                driver_number=int(result["number"]),
                driver_name=(
                    f'{driver["givenName"]} '
                    f'{driver["familyName"]}'
                ),
                team_name=constructor["name"],
                team_color=team_color(
                    constructor["constructorId"]
                ),
                laps=int(result["laps"]),
                gap_to_leader=(
                    result.get("Time", {}).get("time")
                    or result.get("status")
                ),
            )
        )

    if not podium:
        raise HTTPException(
            status_code=502,
            detail="Race result is not available",
        )

    circuit = race["Circuit"]
    location = circuit["Location"]

    return Race(
        year=int(race["season"]),
        round=int(race["round"]),
        race_name=race["raceName"],
        circuit=circuit["circuitName"],
        location=location["locality"],
        country=location["country"],
        date_start=parse_race_datetime(
            race["date"],
            race.get("time"),
        ),
        podium=podium,
    )


async def get_driver_championship_standings(
) -> ChampionshipStandings | None:
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        data = await request_jolpica(
            client,
            "current/driverstandings/",
        )

    standings_lists = (
        data
        .get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )

    if not standings_lists:
        return None

    standings = standings_lists[0]

    championship_drivers = []

    for standing in standings.get(
        "DriverStandings",
        [],
    ):
        driver = standing["Driver"]

        constructors = standing.get(
            "Constructors",
            [],
        )

        constructor = (
            constructors[-1]
            if constructors
            else None
        )

        points = float(standing["points"])

        championship_drivers.append(
            ChampionshipDriver(
                position=int(
                    standing["position"]
                ),
                driver_number=int(
                    driver["permanentNumber"]
                ),
                driver_name=(
                    f'{driver["givenName"]} '
                    f'{driver["familyName"]}'
                ),
                team_name=(
                    constructor["name"]
                    if constructor
                    else "Unknown Team"
                ),
                points=points,
                points_label=format_points(points),
                team_color=(
                    team_color(
                        constructor["constructorId"]
                    )
                    if constructor
                    else "#E10600"
                ),
            )
        )

    if not championship_drivers:
        return None

    return ChampionshipStandings(
        year=int(standings["season"]),
        round=int(standings["round"]),
        drivers=championship_drivers,
    )


async def get_next_race() -> NextRace | None:
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        data = await request_jolpica(
            client,
            "current/next/",
        )

    races = (
        data
        .get("MRData", {})
        .get("RaceTable", {})
        .get("Races", [])
    )

    if not races:
        return None

    race = races[0]

    date_start = parse_race_datetime(
        race["date"],
        race.get("time"),
    )

    days_remaining = (
        date_start.date() - now.date()
    ).days

    if days_remaining <= 0:
        countdown_label = "Today"
    elif days_remaining == 1:
        countdown_label = "Tomorrow"
    else:
        countdown_label = (
            f"{days_remaining} days remaining"
        )

    circuit = race["Circuit"]
    location = circuit["Location"]

    return NextRace(
        year=int(race["season"]),
        round=int(race["round"]),
        race_name=race["raceName"],
        circuit=circuit["circuitName"],
        location=location["locality"],
        country=location["country"],
        date_start=date_start,
        local_start_label=date_start.strftime(
            "%d %B %Y, %H:%M UTC"
        ),
        countdown_label=countdown_label,
    )