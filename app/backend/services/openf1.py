import asyncio
import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from models.race import (
    GridDriver,
    NextRace,
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
    os.getenv(
        "OPENF1_MIN_REQUEST_INTERVAL",
        "0.36",
    ),
)

openf1_request_lock = asyncio.Lock()
last_openf1_request_at = 0.0


def parse_openf1_datetime(
    value: str,
) -> datetime:
    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00"),
    )

    if parsed.tzinfo is None:
        return parsed.replace(
            tzinfo=timezone.utc,
        )

    return parsed


def team_color(
    driver: dict | None,
) -> str:
    if driver is None:
        return BRAND_TEAM_COLOR_FALLBACK

    value = driver.get("team_colour")

    if not value:
        return BRAND_TEAM_COLOR_FALLBACK

    normalized = str(value).strip().lstrip("#")

    if len(normalized) != 6:
        return BRAND_TEAM_COLOR_FALLBACK

    return f"#{normalized}"


def driver_name(
    driver: dict | None,
    driver_number: int,
) -> str:
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


def team_name(
    driver: dict | None,
) -> str:
    if driver is None:
        return "Unknown Team"

    return driver.get("team_name") or "Unknown Team"


def drivers_by_number(
    drivers: list[dict],
) -> dict[int, dict]:
    return {
        driver["driver_number"]: driver
        for driver in drivers
        if driver.get("driver_number") is not None
    }


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
            if entry.get("position") is not None and entry.get("driver_number") is not None
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
                driver_name=driver_name(
                    driver,
                    number,
                ),
                team_name=team_name(driver),
                team_color=team_color(driver),
            )
        )

    return grid_drivers


async def find_race_session(
    client: httpx.AsyncClient,
    next_race: NextRace,
) -> dict | None:
    sessions = await request_openf1(
        client=client,
        endpoint="sessions",
        params={
            "session_type": "Race",
            "year": next_race.year,
        },
    )

    if not sessions:
        return None

    race_date = next_race.date_start.date()

    matching_sessions = [
        session
        for session in sessions
        if session.get("date_start")
        and parse_openf1_datetime(session["date_start"]).date() == race_date
        and not session.get(
            "is_cancelled",
            False,
        )
    ]

    if not matching_sessions:
        return None

    return min(
        matching_sessions,
        key=lambda session: abs(
            (parse_openf1_datetime(session["date_start"]) - next_race.date_start).total_seconds()
        ),
    )


async def get_starting_grid(
    next_race: NextRace | None,
) -> StartingGrid | None:
    if next_race is None:
        return None

    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
    ) as client:
        race_session = await find_race_session(
            client,
            next_race,
        )

        if race_session is None:
            return None

        meeting_key = race_session["meeting_key"]
        session_key = race_session["session_key"]

        official_grid = await request_openf1(
            client=client,
            endpoint="starting_grid",
            params={
                "session_key": session_key,
            },
        )

        official_grid = [
            entry for entry in official_grid if entry.get("meeting_key") == meeting_key
        ]

        if official_grid:
            drivers = await request_drivers(
                client=client,
                session_key=session_key,
                meeting_key=meeting_key,
            )

            grid_drivers = build_grid_drivers(
                grid_entries=official_grid,
                drivers=drivers,
            )

            if grid_drivers:
                return StartingGrid(
                    year=next_race.year,
                    round=next_race.round,
                    title="Starting Grid",
                    is_official=True,
                    drivers=grid_drivers,
                )

        sessions = await request_openf1(
            client=client,
            endpoint="sessions",
            params={
                "meeting_key": meeting_key,
            },
        )

        qualifying_sessions = [
            session
            for session in sessions
            if session.get("session_type") == "Qualifying"
            and not session.get(
                "is_cancelled",
                False,
            )
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

        qualifying_session_key = qualifying_session["session_key"]

        qualifying_results = await request_openf1(
            client=client,
            endpoint="session_result",
            params={
                "session_key": qualifying_session_key,
            },
        )

        if not qualifying_results:
            return None

        drivers = await request_drivers(
            client=client,
            session_key=qualifying_session_key,
            fallback_session_key=session_key,
            meeting_key=meeting_key,
        )

        grid_drivers = build_grid_drivers(
            grid_entries=qualifying_results,
            drivers=drivers,
        )

        if not grid_drivers:
            return None

        return StartingGrid(
            year=next_race.year,
            round=next_race.round,
            title="Qualifying Classification",
            is_official=False,
            drivers=grid_drivers,
        )
