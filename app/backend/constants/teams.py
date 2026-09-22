TEAM_COLORS = {
    "mercedes": "#27F4D2",
    "ferrari": "#E8002D",
    "mclaren": "#FF8000",
    "red_bull": "#3671C6",
    "rb": "#6692FF",
    "alpine": "#00A1E8",
    "haas": "#B6BABD",
    "audi": "#F50537",
    "williams": "#1868DB",
    "aston_martin": "#229971",
    "cadillac": "#FFFFFF",
}

TEAM_COLOR_FALLBACK = "#E10600"


def team_color(constructor_id: str) -> str:
    return TEAM_COLORS.get(
        constructor_id,
        TEAM_COLOR_FALLBACK,
    )
