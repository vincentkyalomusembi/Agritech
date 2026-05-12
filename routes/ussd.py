"""
routes/ussd.py
Africa's Talking USSD callback handler.

Key fixes vs friendly branch:
  - Uses CON / END prefix (required by Africa's Talking — without it the
    session hangs and the user sees a blank screen)
  - Uses text.split("*") navigation instead of server-side state dict.
    This is stateless: the full user path is always in the `text` param,
    so a server restart never breaks an active session.
  - 182-character hard limit on CON responses (USSD truncates silently)
  - Kenya country code appended to county names for OpenWeather accuracy
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from models.recommender import build_recommendation, list_counties
from services.weather import get_weather

router = APIRouter()

MAX_USSD_LEN = 182  # Africa's Talking hard limit for CON responses


# ── Helpers ───────────────────────────────────────────────────────────────────

def con(text: str) -> PlainTextResponse:
    """Continue session — user sees menu, can respond."""
    return PlainTextResponse(f"CON {text[:MAX_USSD_LEN]}")


def end(text: str) -> PlainTextResponse:
    """End session — user sees message, session closes."""
    return PlainTextResponse(f"END {text}")


# ── Main menu ─────────────────────────────────────────────────────────────────

def _main_menu() -> str:
    return (
        "Welcome to Agritech AI 🌾\n"
        "1. Get Farm Recommendation\n"
        "2. About"
    )


# ── County menu ───────────────────────────────────────────────────────────────

def _county_menu() -> str:
    counties = list_counties()
    lines = ["Select your county:"]
    for i, county in enumerate(counties, 1):
        lines.append(f"{i}. {county}")
    return "\n".join(lines)


# ── Farm type menu ────────────────────────────────────────────────────────────

def _farm_type_menu(county: str) -> str:
    return (
        f"County: {county}\n"
        "Select farm type:\n"
        "1. Crop\n"
        "2. Livestock"
    )


# ── Recommendation result ─────────────────────────────────────────────────────

def _recommendation_screen(county: str, farm_type: str) -> str:
    weather = get_weather(county)
    result = build_recommendation(county, farm_type, weather)

    if not result:
        return end(f"Sorry, no data found for {county}. Contact us for support.")

    lines = [
        f"📍 {result['county']} | {result['farm_type'].title()}",
        f"🌱 Soil: {result['soil_type']}",
        f"🌧 Avg Rainfall: {result['avg_rainfall']}mm",
    ]

    if weather:
        src = "live" if weather.get("source") == "openweather" else "est."
        lines.append(f"🌡 Temp: {weather['temp']}°C ({src})")

    lines.append(f"\n✅ Recommended: {result['recommendation'].upper()}")

    for note in result["weather_notes"]:
        lines.append(f"⚠ {note}")

    lines.append("\n0. Back to menu")
    return "\n".join(lines)


# ── USSD router ───────────────────────────────────────────────────────────────

@router.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    """
    Stateless USSD handler using text.split("*") navigation.

    Africa's Talking always sends the full session path in `text`:
        ""         → user just dialled (show main menu)
        "1"        → user pressed 1 on main menu
        "1*2"      → user pressed 1, then 2
        "1*2*1"    → user pressed 1, then 2, then 1
    """
    form = await request.form()
    text: str = form.get("text", "")

    steps = [s for s in text.split("*") if s != ""]

    # ── Level 0: main menu ────────────────────────────────────────────────
    if len(steps) == 0:
        return con(_main_menu())

    # ── Level 1: main menu choice ─────────────────────────────────────────
    if len(steps) == 1:
        choice = steps[0]

        if choice == "1":
            return con(_county_menu())

        if choice == "2":
            return end(
                "Agritech AI — AI-powered farm advice for Kenyan farmers.\n"
                "Powered by real-time weather + local crop data.\n"
                "Dial again to get your recommendation."
            )

        return con(f"Invalid option.\n{_main_menu()}")

    # ── Level 2: county selected ──────────────────────────────────────────
    if len(steps) == 2 and steps[0] == "1":
        counties = list_counties()
        try:
            county_index = int(steps[1]) - 1
            if 0 <= county_index < len(counties):
                selected_county = counties[county_index]
                return con(_farm_type_menu(selected_county))
            else:
                return con(f"Invalid county number.\n{_county_menu()}")
        except ValueError:
            return con(f"Enter a number.\n{_county_menu()}")

    # ── Level 3: farm type selected → show recommendation ─────────────────
    if len(steps) == 3 and steps[0] == "1":
        counties = list_counties()
        try:
            county_index = int(steps[1]) - 1
            if not (0 <= county_index < len(counties)):
                return con(f"Invalid county.\n{_county_menu()}")

            selected_county = counties[county_index]
            farm_choice = steps[2]

            if farm_choice == "1":
                farm_type = "crop"
            elif farm_choice == "2":
                farm_type = "livestock"
            else:
                return con(f"Invalid option.\n{_farm_type_menu(selected_county)}")

            result_text = _recommendation_screen(selected_county, farm_type)
            return end(result_text)

        except ValueError:
            return con("Invalid input. Start again.")

    # ── Handle "0. Back to menu" and any unknown deep path ────────────────
    return con(_main_menu())