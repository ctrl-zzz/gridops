import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

from models.race import (
    ChampionshipDriver,
    ChampionshipStandings,
    GridDriver,
    NextRace,
    PodiumPosition,
    Race,
    StartingGrid,
)


OPENF1_BASE_URL = os.getenv(
    "OPENF1_BASE_URL",
    "https://api.openf1.org/v1",
)

REQUEST_TIMEOUT = float(
    os.getenv("REQUEST_TIMEOUT", "10"),
)

BRAND_TEAM_COLOR_FALLBACK = "#E10600"
OPENF1_MIN_REQUEST_INTERVAL = float(
    os.getenv("OPENF1_MIN_REQUEST_INTERVAL", "0.36"),
)
openf1_request_lock = asyncio.Lock()
last_openf1_request_at = 0.0


def parse_openf1_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00"),
    )

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def parse_openf1_timezone(gmt_offset: str | None) -> timezone:
    if not gmt_offset:
        return timezone.utc

    sign = -1 if gmt_offset.startswith("-") else 1
    offset_parts = gmt_offset.lstrip("+-").split(":")

    try:
        hours = int(offset_parts[0])
        minutes = int(offset_parts[1])
        seconds = int(float(offset_parts[2])) if len(offset_parts) > 2 else 0
    except (IndexError, ValueError):
        return timezone.utc

    return timezone(
        sign * timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )
    )


def team_color(driver: dict | None) -> str:
    if driver is None:
        return BRAND_TEAM_COLOR_FALLBACK

    value = driver.get("team_colour")

    if not value:
        return BRAND_TEAM_COLOR_FALLBACK

    normalized = str(value).strip().lstrip("#")

    if len(normalized) != 6:
        return BRAND_TEAM_COLOR_FALLBACK

    return f"#{normalized}"


def driver_name(driver: dict | None, driver_number: int) -> str:
    if driver is None:
        return f"Driver {driver_number}"

    return (
        driver.get("full_name")
        or driver.get("broadcast_name")
        or " ".join(
            part
            for part in [
                driver.get("first_name"),
                driver.get("last_name"),
            ]
            if part
        )
        or f"Driver {driver_number}"
    )


def team_name(driver: dict | None) -> str:
    if driver is None:
        return "Unknown Team"

    return driver.get("team_name") or "Unknown Team"


def drivers_by_number(drivers: list[dict]) -> dict[int, dict]:
    return {
        driver["driver_number"]: driver
        for driver in drivers
        if driver.get("driver_number") is not None
    }


def format_points(points: float) -> str:
    if float(points).is_integer():
        return str(int(points))

    return f"{points:g}"


async def request_drivers(
    client: httpx.AsyncClient,
    session_key: int,
    fallback_session_key: int | None = None,
    meeting_key: int | None = None,
) -> list[dict]:
    drivers = await request_openf1(
        client=client,
        endpoint="drivers",
        params={
            "session_key": session_key,
        },
    )

    if drivers:
        return drivers

    if fallback_session_key is not None and fallback_session_key != session_key:
        drivers = await request_openf1(
            client=client,
            endpoint="drivers",
            params={
                "session_key": fallback_session_key,
            },
        )

    if drivers:
        return drivers

    if meeting_key is None:
        return []

    return await request_openf1(
        client=client,
        endpoint="drivers",
        params={
            "meeting_key": meeting_key,
        },
    )


def build_grid_drivers(
    grid_entries: list[dict],
    drivers: list[dict],
) -> list[GridDriver]:
    driver_lookup = drivers_by_number(drivers)

    ordered_entries = sorted(
        [
            entry
            for entry in grid_entries
            if entry.get("position") is not None
            and entry.get("driver_number") is not None
        ],
        key=lambda entry: entry["position"],
    )

    grid_drivers = []

    for entry in ordered_entries:
        number = entry["driver_number"]
        driver = driver_lookup.get(number)

        grid_drivers.append(
            GridDriver(
                position=entry["position"],
                driver_number=number,
                driver_name=driver_name(driver, number),
                team_name=team_name(driver),
                team_color=team_color(driver),
            )
        )

    return grid_drivers


async def request_openf1(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict,
) -> list[dict]:
    global last_openf1_request_at

    url = f"{OPENF1_BASE_URL}/{endpoint}"

    try:
        async with openf1_request_lock:
            loop = asyncio.get_running_loop()
            elapsed = loop.time() - last_openf1_request_at

            if elapsed < OPENF1_MIN_REQUEST_INTERVAL:
                await asyncio.sleep(OPENF1_MIN_REQUEST_INTERVAL - elapsed)

            last_openf1_request_at = loop.time()

        response = await client.get(
            url,
            params=params,
        )

        response.raise_for_status()
        return response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="OpenF1 request timed out",
        ) from exc

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return []

        raise HTTPException(
            status_code=502,
            detail="OpenF1 API is unavailable",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenF1 API is unavailable",
        ) from exc


async def get_latest_race() -> Race:
    current_year = datetime.now(timezone.utc).year
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:

        sessions = await request_openf1(
            client=client,
            endpoint="sessions",
            params={
                "session_type": "Race",
                "year": current_year,
            },
        )

        completed_races = [
            session
            for session in sessions
            if session["session_name"] == "Race"
            and not session.get("is_cancelled", False)
            and parse_openf1_datetime(session["date_end"]) < now
        ]

        if not completed_races:
            raise HTTPException(
                status_code=404,
                detail="No completed Formula 1 race found",
            )

        latest_session = max(
            completed_races,
            key=lambda session: parse_openf1_datetime(session["date_end"]),
        )

        session_key = latest_session["session_key"]

        results = await request_openf1(
            client=client,
            endpoint="session_result",
            params={
                "session_key": session_key,
            },
        )

        drivers = await request_openf1(
            client=client,
            endpoint="drivers",
            params={
                "session_key": session_key,
            },
        )

    driver_by_number = drivers_by_number(drivers)

    podium_results = sorted(
        [
            result
            for result in results
            if result.get("position") in {1, 2, 3}
        ],
        key=lambda result: result["position"],
    )

    podium = []

    for result in podium_results:
        driver_number = result["driver_number"]
        driver = driver_by_number.get(driver_number)

        if driver is None:
            continue

        podium.append(
            PodiumPosition(
                position=result["position"],
                driver_number=driver_number,
                driver_name=driver_name(driver, driver_number),
                team_name=team_name(driver),
                team_color=team_color(driver),
                laps=result.get("number_of_laps"),
                gap_to_leader=result.get("gap_to_leader"),
            )
        )

    if not podium:
        raise HTTPException(
            status_code=502,
            detail="Race result is not available",
        )

    return Race(
        meeting_key=latest_session["meeting_key"],
        session_key=session_key,
        year=latest_session["year"],
        circuit=latest_session["circuit_short_name"],
        location=latest_session["location"],
        country=latest_session["country_name"],
        date_start=parse_openf1_datetime(latest_session["date_start"]),
        date_end=parse_openf1_datetime(latest_session["date_end"]),
        podium=podium,
    )


async def get_next_race() -> NextRace | None:
    now = datetime.now(timezone.utc)
    years = [
        now.year,
        now.year + 1,
    ]

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        sessions = []
        future_races = []

        for year in years:
            sessions.extend(
                await request_openf1(
                    client=client,
                    endpoint="sessions",
                    params={
                        "session_type": "Race",
                        "year": year,
                    },
                )
            )

            future_races = [
                session
                for session in sessions
                if session.get("session_name") == "Race"
                and not session.get("is_cancelled", False)
                and parse_openf1_datetime(session["date_end"]) >= now
            ]

            if future_races:
                break

        if not future_races:
            return None

        next_session = min(
            future_races,
            key=lambda session: parse_openf1_datetime(session["date_start"]),
        )

        meetings = await request_openf1(
            client=client,
            endpoint="meetings",
            params={
                "meeting_key": next_session["meeting_key"],
            },
        )

    meeting = meetings[0] if meetings else {}
    date_start = parse_openf1_datetime(next_session["date_start"])
    date_end = parse_openf1_datetime(next_session["date_end"])
    local_timezone = parse_openf1_timezone(
        next_session.get("gmt_offset") or meeting.get("gmt_offset"),
    )
    local_start = date_start.astimezone(local_timezone)
    now_local = now.astimezone(local_timezone)
    days_remaining = (local_start.date() - now_local.date()).days

    if days_remaining <= 0:
        countdown_label = "Today"
    elif days_remaining == 1:
        countdown_label = "Tomorrow"
    else:
        countdown_label = f"{days_remaining} days remaining"

    return NextRace(
        meeting_key=next_session["meeting_key"],
        session_key=next_session["session_key"],
        year=next_session["year"],
        race_name=(
            meeting.get("meeting_name")
            or meeting.get("meeting_official_name")
            or f"{next_session['country_name']} Grand Prix"
        ),
        circuit=next_session["circuit_short_name"],
        location=next_session["location"],
        country=next_session["country_name"],
        date_start=date_start,
        date_end=date_end,
        local_start_label=local_start.strftime("%d %B %Y, %H:%M local"),
        countdown_label=countdown_label,
    )


async def get_starting_grid(next_race: NextRace | None) -> StartingGrid | None:
    if next_race is None:
        return None

    now = datetime.now(timezone.utc)

    if next_race.date_end < now:
        return None

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        official_grid = await request_openf1(
            client=client,
            endpoint="starting_grid",
            params={
                "session_key": next_race.session_key,
            },
        )

        official_grid = [
            entry
            for entry in official_grid
            if entry.get("meeting_key") == next_race.meeting_key
        ]

        if official_grid:
            drivers = await request_drivers(
                client=client,
                session_key=next_race.session_key,
                meeting_key=next_race.meeting_key,
            )
            grid_drivers = build_grid_drivers(
                grid_entries=official_grid,
                drivers=drivers,
            )

            if grid_drivers:
                return StartingGrid(
                    meeting_key=next_race.meeting_key,
                    session_key=next_race.session_key,
                    title="Starting Grid",
                    is_official=True,
                    drivers=grid_drivers,
                )

        sessions = await request_openf1(
            client=client,
            endpoint="sessions",
            params={
                "meeting_key": next_race.meeting_key,
            },
        )

        qualifying_sessions = [
            session
            for session in sessions
            if session.get("session_type") == "Qualifying"
            and not session.get("is_cancelled", False)
            and session.get("date_end")
            and parse_openf1_datetime(session["date_end"]) <= now
        ]

        if not qualifying_sessions:
            return None

        qualifying_session = max(
            qualifying_sessions,
            key=lambda session: (
                session.get("session_name") == "Qualifying",
                parse_openf1_datetime(session["date_end"]),
            ),
        )

        qualifying_results = await request_openf1(
            client=client,
            endpoint="session_result",
            params={
                "session_key": qualifying_session["session_key"],
            },
        )

        if not qualifying_results:
            return None

        drivers = await request_drivers(
            client=client,
            session_key=qualifying_session["session_key"],
            fallback_session_key=next_race.session_key,
            meeting_key=next_race.meeting_key,
        )
        grid_drivers = build_grid_drivers(
            grid_entries=qualifying_results,
            drivers=drivers,
        )

        if not grid_drivers:
            return None

        return StartingGrid(
            meeting_key=next_race.meeting_key,
            session_key=qualifying_session["session_key"],
            title="Qualifying Classification",
            is_official=False,
            drivers=grid_drivers,
        )


async def get_driver_championship_standings(
    race: Race,
) -> ChampionshipStandings | None:
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        standings = await request_openf1(
            client=client,
            endpoint="championship_drivers",
            params={
                "session_key": race.session_key,
            },
        )

        if not standings:
            return None

        drivers = await request_drivers(
            client=client,
            session_key=race.session_key,
            meeting_key=race.meeting_key,
        )

    driver_lookup = drivers_by_number(drivers)
    ordered_standings = sorted(
        [
            (index, standing)
            for index, standing in enumerate(standings)
            if standing.get("driver_number") is not None
        ],
        key=lambda indexed_standing: (
            -float(indexed_standing[1].get("points_current") or 0),
            indexed_standing[1].get("position_current")
            if indexed_standing[1].get("position_current") is not None
            else len(standings) + indexed_standing[0],
            indexed_standing[0],
        ),
    )

    championship_drivers = []

    for ranking_index, (_, standing) in enumerate(ordered_standings, start=1):
        number = standing["driver_number"]
        driver = driver_lookup.get(number)
        points = float(standing.get("points_current") or 0)

        championship_drivers.append(
            ChampionshipDriver(
                position=standing.get("position_current") or ranking_index,
                driver_number=number,
                driver_name=driver_name(driver, number),
                team_name=team_name(driver),
                points=points,
                points_label=format_points(points),
                team_color=team_color(driver),
            )
        )

    if not championship_drivers:
        return None

    return ChampionshipStandings(
        meeting_key=race.meeting_key,
        session_key=race.session_key,
        year=race.year,
        drivers=championship_drivers,
    )
