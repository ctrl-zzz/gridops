import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from models.race import PodiumPosition, Race


OPENF1_BASE_URL = os.getenv(
    "OPENF1_BASE_URL",
    "https://api.openf1.org/v1",
)

REQUEST_TIMEOUT = float(
    os.getenv("REQUEST_TIMEOUT", "10"),
)


async def request_openf1(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict,
) -> list[dict]:
    url = f"{OPENF1_BASE_URL}/{endpoint}"

    try:
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
            and datetime.fromisoformat(session["date_end"]) < now
        ]

        if not completed_races:
            raise HTTPException(
                status_code=404,
                detail="No completed Formula 1 race found",
            )

        latest_session = max(
            completed_races,
            key=lambda session: datetime.fromisoformat(
                session["date_end"]
            ),
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

    driver_by_number = {
        driver["driver_number"]: driver
        for driver in drivers
    }

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

        team_color = "#E10600"

        if driver.get("team_colour"):
            team_color = f"#{driver['team_colour']}"

        podium.append(
            PodiumPosition(
                position=result["position"],
                driver_number=driver_number,
                driver_name=driver["full_name"],
                team_name=driver["team_name"],
                team_color=team_color,
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
        session_key=session_key,
        year=latest_session["year"],
        circuit=latest_session["circuit_short_name"],
        location=latest_session["location"],
        country=latest_session["country_name"],
        date_start=latest_session["date_start"],
        date_end=latest_session["date_end"],
        podium=podium,
    )